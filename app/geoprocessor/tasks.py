from os import getenv
from os.path import join, splitext
from shutil import make_archive
import time
import json

import asyncio
import numpy as np
from PIL import Image

from celery import Celery

from geoprocessor.utils.object_detection import (
    read_tf_label_map,
    prep_objdetect_project,
    calc_max_gsd,
    resize_to_gsd,
    chip_geo_image,
    unchip_geo_image,
    batch_inference,
    results_dict_to_dataframe,
    plot_bboxes_on_image,
    collate_per_image_results,
)


print("=== TASKS.PY ===")

celery_config_module = getenv(
    "CELERY_CONFIG_MODULE", "geoprocessor.configs.celery_config"
)
print(f"CELERY_CONFIG_MODULE: {celery_config_module}")

celery_app = Celery()
celery_app.config_from_envvar("CELERY_CONFIG_MODULE")
# celery.config_from_object(celery_config)


@celery_app.task(name="object_detection")  # Named task
def object_detection(
    task_folder,
    images_to_process,
    sensor_name,
    sensor_params,
    color_map_path,
    label_map_path,
):
    """
    Given a batch of images:
    1. Resample to target GSD
    2. Chip image
    3. Run the object detection
    4. Un-chip the results
    5. Format the results:
        - Image Plots
        - CSV of detections
          - corners, centerpoints, size
        - JSON of detections
        - Per-class debris counts, cumulative sum, average size
    """

    # ------------------------------------------------
    # PREP PROJECT FOLDERS, LOAD USER-SUBMITTED PARAMS
    # ------------------------------------------------
    task_paths = prep_objdetect_project(task_folder)

    with open(join(task_folder, "user_submission.json"), "rb") as sub:
        user_sub = json.load(sub)

    # -----------------------------
    # BEGIN INFERENCE ON EACH IMAGE
    # -----------------------------
    for current_image in images_to_process:
        print(f"Processing: {current_image}")

        i_path = join(task_folder, current_image)
        i_basename, i_ext = splitext(current_image)

        # ----------------------------------------------------------------
        # IF RESAMPLE=True, THEN CALCULATE GSD AND RESAMPLE THE O.G. IMAGE
        # ----------------------------------------------------------------
        if user_sub["skip_optional_resampling"] is False:
            print(f"Resampling image {current_image}...")

            with Image.open(i_path, mode="r") as in_image:
                if in_image.mode != "RGB":
                    in_image = in_image.convert("RGB")

                image_height, image_width = in_image.size

                max_gsd = calc_max_gsd(
                    user_sub["flight_AGL"],
                    image_height,
                    image_width,
                    list(user_sub["api_sensor_params"]),
                )

                print(
                    f"the {current_image}'s GSD was automatically computed to be \
                    {max_gsd} centimeters. Images are going to be resampled to the \
                    API's target GSD of {user_sub['target_gsd_cm']} centimeters."
                )

                processed_image = resize_to_gsd(
                    in_image, max_gsd, user_sub["api_target_gsd"]
                )

                resampled_path = join(
                    task_paths["tmp_path"], f"{i_basename}_resample{i_ext}"
                )
                processed_image.save(resampled_path)
                print(
                    f"... resampling complete! Image resampled from {in_image.size} \
                    to {processed_image.size}."
                )
        # ------------------------------------------
        # ELIF RESAMPLING=False, THEN USE O.G. IMAGE
        # ------------------------------------------
        elif user_sub["skip_optional_resampling"] is True:
            print(f"User declined resampling of {current_image}.")
            resampled_path = i_path

        # ----------------------------------
        # CHIP LARGE IMAGE FOR TF INFERENCE
        # ----------------------------------
        with Image.open(resampled_path) as in_image:
            if in_image.mode != "RGB":
                in_image = in_image.convert("RGB")

            image_array = np.array(in_image, dtype=np.uint8)
            chip_array, tl_array, meta_dict = chip_geo_image(
                image_array, kernel_size=user_sub["chip_size"]
            )

        # -------------------------
        # INFERENCE WITH TENSORFLOW
        # -------------------------
        start = time.time()  # start the clock
        predictions = asyncio.run(
            batch_inference(chip_array, user_sub["confidence_threshold"], concurrency=1)
        )

        end = time.time()
        total_time = end - start
        time_per_chips = total_time / len(chip_array)
        print(f"{len(predictions)} of {len(chip_array)} chips had detections.")
        print(
            f"All chips were processed in {total_time} seconds. \
            This is {time_per_chips} seconds per chip."
        )
        # -----------------------------
        # UN-CHIP THE INFERENCE RESULTS
        # -----------------------------
        final_results_dict = unchip_geo_image(
            i_basename,
            predictions,
            tl_array,
            meta_dict["chip_height"],
            meta_dict["chip_width"],
        )

        # -----------------------------
        # PLOT RESULTS ON IMAGES, WRITE
        # -----------------------------
        with open(color_map_path, "rb") as color_map:
            color_map_dict = json.load(color_map)

        label_map_dict = read_tf_label_map(label_map_path)

        image_plot = plot_bboxes_on_image(
            i_path, final_results_dict[i_basename], color_map_dict, label_map_dict
        )

        out_image_path = join(
            task_paths["results_path"], f"{i_basename}_results{i_ext}"
        )

        image_plot.save(out_image_path)
        print(f"Wrote {out_image_path}")

        # ------------------
        # WRITE JSON RESULTS
        # ------------------
        json_results_path = join(
            task_paths["per_results_path"], f"{i_basename}_debris_objects.json"
        )
        with open(json_results_path, mode="w", encoding="utf-8") as outfile:
            json.dump(final_results_dict, outfile, indent=3)

        # ------------------
        # WRITE CSV RESULTS
        # ------------------
        results_df = results_dict_to_dataframe(
            i_basename, final_results_dict[i_basename], label_map_dict
        )
        csv_results_path = join(
            task_paths["per_results_path"], f"{i_basename}_debris_objects.csv"
        )
        results_df.to_csv(csv_results_path, index=False)
        print(f"Wrote {csv_results_path}")

        print(f"Completed processing of {current_image}.")

    # -------------------------
    # COLLATE TOTAL RESULTS
    # -------------------------
    print("Completed processing of all images. Zipping final results...")

    final_results_df, final_counts_series = collate_per_image_results(
        task_paths["per_results_path"]
    )

    final_df_path = join(task_paths["results_path"], "all_debris_objects.csv")
    final_results_df.to_csv(final_df_path, index=False)

    final_counts_path = join(task_paths["results_path"], "debris_type_counts.csv")
    final_counts_series.to_csv(
        final_counts_path, index_label=["class"], header=["count"]
    )

    # ZIP + RETURN RESULT
    zip_no_ext = join(task_folder, "inference_results")
    make_archive(zip_no_ext, "zip", task_paths["results_path"])

    zipped_api_results = zip_no_ext + ".zip"

    print(f"Finished! Final results are ready at {zip_no_ext}.zip")

    return zipped_api_results
