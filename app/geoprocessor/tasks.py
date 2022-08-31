from os import getenv
from os.path import join, splitext
import time
import json

import asyncio
import numpy as np
from PIL import Image

from celery import Celery

from utils.object_detection import (
    setup_objdetect_project,
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
print(f'CELERY_CONFIG_MODULE: {getenv("CELERY_CONFIG_MODULE")}')

celery_app = Celery()
celery_app.config_from_envvar("CELERY_CONFIG_MODULE")
# celery.config_from_object(celery_config)


@celery_app.task(name="object_detection")  # Named task
def non_georef_object_detection(
    image_path,
    images_to_process,
    sensor_params,
    color_scheme,
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

    # Prep project folder, load user-submitted parameters
    (processing_directory, plot_directory, tab_directory) = setup_objdetect_project(
        image_path
    )

    with open(f"{image_path}/user_submission.json", "rb") as sub:
        user_sub = json.load(sub)

    # Begin inference on images...
    for current_image in images_to_process:
        print(f"Processing: {current_image}")

        i_path = join(image_path, current_image)
        i_basename, i_ext = splitext(current_image)

        # Resample the image if needed
        if user_sub["skip_optional_resampling"] is False:
            print(f"Resampling image {current_image}...")

            with Image.open(i_path, mode="r") as in_image:
                if in_image.mode != "RGB":
                    in_image = in_image.convert("RGB")

                image_height, image_width = in_image.size

                (focal_length_mm, sensor_height_cm, sensor_width_cm) = sensor_params[
                    user_sub["sensor_platform"]
                ]
                # print(f"Focal length: {focal_length_mm}, \
                #     Sensor height: {sensor_height_cm}, \
                #     Sensor width: {sensor_width_cm}")

                max_gsd = calc_max_gsd(
                    user_sub["flight_AGL"],
                    focal_length_mm,
                    image_height,
                    image_width,
                    sensor_height_cm,
                    sensor_width_cm,
                )

                print(
                    f"the {current_image}'s GSD was automatically computed to be \
                    {max_gsd} centimeters. Images are going to be resampled to the \
                    API's target GSD of {user_sub['target_gsd_cm']} centimeters."
                )

                processed_image = resize_to_gsd(
                    in_image, max_gsd, user_sub["target_gsd_cm"]
                )

                resampled_path = join(
                    processing_directory, f"{i_basename}_resample{i_ext}"
                )
                processed_image.save(resampled_path)
                print(
                    f"... resampling complete! Image resampled from {in_image.size} \
                    to {processed_image.size}."
                )
        elif user_sub["skip_optional_resampling"] is True:
            print(f"User declined resampling of {current_image}.")
            resampled_path = i_path

        # Pre-process image for inference.
        with Image.open(resampled_path) as in_image:
            if in_image.mode != "RGB":
                in_image = in_image.convert("RGB")

            image_array = np.array(in_image, dtype=np.uint8)
            chip_array, tl_array, meta_dict = chip_geo_image(
                image_array, kernel_size=user_sub["chip_size"]
            )

        # Inference with Tensorflow Serving.
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

        # POST-PROCESS SINGLE IMAGE RESULTS
        final_results_dict = unchip_geo_image(
            i_basename,
            predictions,
            tl_array,
            meta_dict["chip_height"],
            meta_dict["chip_width"],
        )

        # CREATE IMAGE PLOTS + PER-IMAGE DATA
        image_plot = plot_bboxes_on_image(
            i_path, final_results_dict[i_basename], color_scheme, label_map
        )

        out_image_path = join(plot_directory, f"{i_basename}_plot{i_ext}")
        image_plot.save(out_image_path)
        print(f"Wrote {out_image_path}")

        # CREATE TABULAR RESULTS (JSON, CSV)
        json_results_path = join(tab_directory, f"{i_basename}_inference_results.json")
        with open(json_results_path, mode="w", encoding="utf-8") as outfile:
            json.dump(final_results_dict, outfile, indent=3)

        csv_results_path = join(tab_directory, f"{i_basename}_inference_results.csv")
        results_df = results_dict_to_dataframe(
            i_basename, final_results_dict[i_basename], label_map
        )
        results_df.to_csv(csv_results_path, index=False)
        print(f"Wrote {csv_results_path}")

        print(f"Completed processing of {current_image}.")

    print("Completed processing of all images. Zipping final results...")

    final_results_df, final_counts_ser = collate_per_image_results(tab_directory)

    final_df_path = join(results_directory, "inference_results.csv")
    final_results_df.to_csv(final_df_path, index=False)

    final_counts_path = join(results_directory, "inference_results_by_debris.csv")
    final_counts_ser.to_csv(final_counts_path, index_label=["class"], header=["count"])

    # ZIP + RETURN RESULT
    zip_no_ext = join(image_path, "inference_results")
    make_archive(zip_no_ext, "zip", results_directory)

    zipped_api_results = zip_no_ext + ".zip"

    print(f"Finished! Final results are ready at {zip_no_ext}.zip")

    return zipped_api_results

    time.sleep(10)
    return {"status": "SUCCESS"}
