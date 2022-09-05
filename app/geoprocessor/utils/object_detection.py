"""This module (geoprocessor.utils.object_detection) contains the main functions for the
pre-/post-processing of both georeferenced and non-georeferenced object detection
results."""

from os import listdir, mkdir
from os.path import join, exists
import math
import json
import csv

import asyncio
import aiohttp

import numpy as np
import pandas as pd

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


def prep_objdetect_project(task_path):
    """A simple function designed to create the necessary directories for API
    object detection processing and results.

    Parameters:
    - task_path: A path-like object where the object detection tasks' project subdirs
        will be created.

    Returns:
    - task_paths: A dictionary representing all of our project's paths. This is
        intended to be passed to the API's object detection task.

    """
    # Create an directory to store the API's intermediate processing files.
    tmp_path = join(task_path, "tmp")
    if not exists(tmp_path):
        mkdir(tmp_path)

    # Create a directory to store final results along with two sub-directories. One
    # for per-image plots, another for per-image tabular results (such as CSV and
    # JSON files).
    results_path = join(task_path, "api_results")
    if not exists(results_path):
        mkdir(results_path)

    per_plots_path = join(results_path, "per_image_plots")
    if not exists(per_plots_path):
        mkdir(per_plots_path)

    per_results_path = join(results_path, "per_image_results")
    if not exists(per_results_path):
        mkdir(per_results_path)

    task_paths = {
        'tmp_path': tmp_path,
        'results_path': results_path,
        'per_plots_path': per_plots_path,
        'per_results_path': per_results_path,
    }

    return task_paths


def ndv_check(chip: np.ndarray, verbose=False) -> bool:
    """This function checks to see if the chip is potentially composed of all NDV values
    and returns either 'True' or 'False'. This is useful for filtering 'blank' chips
    before costly processing operations.

    In an attempt to be NDV-encoding agnostic, this function considers a chip to be
    'blank' when it is composed entirely of common geospatial no data values (NDVs)
    across all dimensions of the image array.

    The common NDVs are defined as either all:
      1. zeros (0)
         OR
      2. the max value for the chip's dtype (example: 255 for np.uint8)

    Inputs:
      - chip: an np.ndarray. Most likely a single chip from the array generated by the
        chip_geo_image() function.
      - verbose: a boolean. If True, the function will print the results of each
        chip evaulation.

    Returns:
      - is_ndv: a True or False (bool) value indicating whether the chip is a 'blank'
      NDV chip (which you would most likely want to discard).
    """

    # NOTE: This may break for float rasters. np.iinfo only works for
    # dtype int (np.finfo for floats)
    max_value = np.iinfo(chip.dtype).max

    if verbose is True:
        print(f"max_value for chip's dtype of {chip.dtype} is {max_value}.")

    maxes = np.ones_like(chip, dtype=np.uint8) * max_value
    zeros = np.zeros_like(chip, dtype=np.uint8)

    is_ndv = False
    if np.array_equal(maxes, chip) is True or np.array_equal(zeros, chip):
        if verbose is True:
            print("NDV Chip.")
        is_ndv = True
    else:
        if verbose is True:
            print("Valid Chip.")
        is_ndv = False

    return is_ndv


def chip_geo_image(
    image: np.ndarray, kernel_size: tuple, nodata_value=0, thin_nodata_chips=False,
    on_disk_path="None",
) -> tuple:
    """This is an ultra-fast, full-featured chipping function adapted from this article:
    https://towardsdatascience.com/efficiently-splitting-an-image-into-tiles-in-python-using-numpy-d1bf0dd7b6f7

    This function "chips" a large image into many contiguous smaller chunks based on the
    user's kernel size. This is desirable for geospatial machine learning (ML) since
    images of the earth tend to be quite large (~10,000 x 10,000 pixels or larger),
    wheras ML tends to prefer images on the order of ~1,000 x 1000 pixels or smaller.

    Since this function is primarily concerned with geospatial images, the function pads
    the image with no data values (NDVs) along the right and bottom sides of the input
    image. This avoids any resampling of the input image, ensuring small features are
    not lost and object shape/size/position are not distorted.

    All the "chipping parameters" are written to two metadata files:
    1) a list of top-left chip coordinates AND
    2) a metadata dictionary with input image/output chip image parameters.

    Taken together, these two files should allow the chips (and any subsequent ML
    prediction results) to be easily back-converted to the input image's shape.

    SEE ALSO: the unchip_geo_chip() function, which utilizes the two metadata files
    to perform the inverse of this operation (i.e., back-convert chip coordinates).

    Inputs:
    - image: a numpy array of the image to be chipped.
    - kernel_size: a tuple of the form (height, width) that defines the desired chip
      size (in pixels). Example: (512, 512) produces chips of size 512 x 512 pixels.
    - nodata_value (optional, default=0): the input image's no-data value. This is
      the value that defines which pixels should be masked in a geospatial image.
      This value is used to pad the image and optionally thin chips that contain
      nothing but NDVs. If non-geo data is coming in, this value should be set to
      0 to create standard black borders.
    - thin_nodata_chips (optional, default=False): a boolean. If True, this function
      will filter out any chips that contain only no-data values.
    - on_disk_path: a string (optional, default='None'). If not 'None', this function
      will write the image chips and their metadata to disk. The chips will not be
      saved in RAM.  This is useful for large images that are too large to fit in
      the host machine's memory.

    Returns:
    - returns: a 3-item Tuple with either file paths or in-memory files:

      The tuple contains the following when on_disk_path is 'None':
      - single_index_array: a np.ndarray of the form:
        [num_chips, chip_height, chip_width, chip_channels]. Which contains the
        image chips.
      - tl_array: a np.ndarray of form [num_chips, chip_top_px, chip_left_px]. The order
        corresponds to the single_index_array.
      - metadata_dict: a dictionary containing various metadata about the image
        chipping/filtering operations.

      This contains the following when on_disk_path is NOT 'None':
      - chip_paths: a string. The path to the directory containing the image chips.
      - tl_path: a string. The path to a CSV file containing the top-left chip
        coordinates.
      - meta_path: a string. The path to a JSON file containing the metadata dictionary.
    """

    img_height, img_width, channels = image.shape
    tile_height, tile_width = kernel_size

    # determine the number of chips in each direction
    num_height_tiles = math.ceil(img_height / tile_height)
    num_width_tiles = math.ceil(img_width / tile_width)
    print(
        f"Input kernel size of {kernel_size} will result in \
        {num_height_tiles * num_width_tiles} output image chips..."
    )

    # determine how much padding is needed
    height_pad = (tile_height * num_height_tiles) - img_height
    width_pad = (tile_width * num_width_tiles) - img_width

    # pad the image with a constant value that matches NDV
    padded_image = np.pad(
        image,
        [(0, height_pad), (0, width_pad), (0, 0)],
        mode="constant",
        constant_values=nodata_value,
    )

    # this is where the "real" magic happens.
    tiled_array = padded_image.reshape(
        num_height_tiles, tile_height, num_width_tiles, tile_width, channels
    )
    tiled_array = tiled_array.swapaxes(1, 2)

    # reshape the chip array so all image chips are along a single axis.
    # This will reshape to our final shape of:
    # (num_chips, kernel height, kernel width, image channels).
    single_index_array = tiled_array.reshape(-1, *(tile_height, tile_width, channels))

    # down the road we may need to reshape the chips back into the padded image.
    # Here we compile a 'metadata dictionary' to potentially help with that process.
    meta_dict = {
        "padded_image_height": padded_image.shape[0],
        "padded_image_width": padded_image.shape[1],
        "num_height_chips": num_height_tiles,
        "num_width_chips": num_width_tiles,
        "chip_height": tile_height,
        "chip_width": tile_width,
        "channels": channels,
    }

    # it may also be helpful to be able to associate each chip's top left
    # pixel coordinate with the original image. The following assembles an
    # array of the top-left corner pixel coordinates in same order as
    # single_index_array.
    # Note that values for these are capped as uint32s(0 to 65,535 pixels) to
    # avoid memory issues.
    tops = np.array(
        [y * tile_height for y in range(0, num_height_tiles)], dtype=np.uint32
    )
    lefts = np.array(
        [x * tile_width for x in range(0, num_width_tiles)], dtype=np.uint32
    )

    tl_pairs = []
    for top in tops:
        for left in lefts:
            new_pair = (top, left)
            tl_pairs.append(new_pair)

    tl_array = np.asarray(tl_pairs, dtype=np.uint32)

    # optionally thin the chips that only contain only NDV values across all 3 bands.
    # Also thin the associated tl_array.
    if thin_nodata_chips is True:
        idxs_to_delete = []
        for i, chip in enumerate(single_index_array):
            if ndv_check(chip) is True:
                idxs_to_delete.append(i)

        single_index_array = np.delete(single_index_array, idxs_to_delete, axis=0)
        tl_array = np.delete(tl_array, idxs_to_delete, axis=0)
        print(
            f"Thinned {len(idxs_to_delete)} NDV chips. \
          Total number of chips after thinning: {len(single_index_array)}."
        )

    print(
        f"Geospatial chipping operation complete. \
      Final chipped array shape: {single_index_array.shape}"
    )

    # if operating in "on-disk" mode, write the outputs to disk.
    if on_disk_path != "None":
        # TODO: use rio to also save geo-coding? Need to test speed...
        # write chips to individual image files

        chip_paths = []
        for i in range(0, single_index_array.shape[0]):
            chip_name = f"{i}.tif"
            chip_path = join(on_disk_path, chip_name)
            chip_paths.append(chip_path)

            Image.fromarray(single_index_array[i]).save(chip_path)
            # print(f"Wrote chip {i} to disk at location {chip_path}")

        # add some additional info and write meta_dict to disk
        meta_dict["num_thinned"] = len(idxs_to_delete)
        meta_dict["thinned_chips"] = idxs_to_delete

        meta_path = join(on_disk_path, "fast_retile_meta.json")
        with open(meta_path, mode="w", encoding="utf-8") as out_file:
            json.dump(meta_dict, out_file)

        # write the TL pairs and a field header to CSV
        fields = ["y", "x"]
        rows = tl_array.tolist()

        tl_path = join(on_disk_path, "chip_toplefts.csv")
        with open(tl_path, mode="w", encoding="utf-8") as out_file:
            write = csv.writer(out_file)
            write.writerow(fields)
            write.writerows(rows)

        # If operating "on-disk", return the paths to each written file
        returns = (chip_paths, tl_path, meta_path)
    else:
        # If operating "in-memory", return the arrays/dicts
        returns = (single_index_array, tl_array, meta_dict)

    return returns


def unchip_geo_image(
    img_basename, inference_results_dict, toplefts_array, chip_height, chip_width
):
    """This function reassembles the chipped results received from Tensorflow Serving.
    The reassembly requires the TF Server's inference results in addition to the
    metadata about the chipping operation (outputs from chip_geo_image()).
    Inputs:
    - img_basename: A string representing the original image's filename (no extension).
    - inference_results_dict: A dictionary containing the multi-class object detection
        results from TF Serving.
    - toplefts_array: A numpy array containing the topleft coordinates of each chip,
        this is generated by the chip_geo_image() function.
    - chip_height: An integer representing the height of the chip in pixels.
    - chip_width: An integer representing the width of the chip in pixels.
    Returns:
    - merged_results_dict: A dictionary containing the reassembled inference results
        from TF Serving.
    """

    merged_results_dict = {}
    new_bboxes = []
    new_scores = []
    new_classes = []

    for i, i_results in inference_results_dict.items():
        y_offset = toplefts_array[i][0]
        x_offset = toplefts_array[i][1]

        for normalized_bbox in i_results["detection_boxes"]:
            bbox = _denormalize_coordinates(normalized_bbox, chip_height, chip_width)
            new_bbox = (
                int(y_offset + bbox[0]),
                int(x_offset + bbox[1]),
                int(y_offset + bbox[2]),
                int(x_offset + bbox[3]),
            )
            new_bboxes.append(new_bbox)

        for score in i_results["detection_scores"]:
            new_scores.append(score)

        for classes in i_results["detection_classes"]:
            new_classes.append(classes)

    merged_results_dict[img_basename] = {
        "bboxes": new_bboxes,
        "scores": new_scores,
        "classes": new_classes,
    }

    return merged_results_dict


async def _async_post(session, url, batch, i, results, raw_conf_threshold=0.0):
    """An async function for submitting batches of image chips to a TensorFlow
    Serving server using the HTTP POST method.
    This function also employs memory-saving features. Specifically:
      1. Only the predictions' score, class, and bounding box are saved.
      2. The dypes of each prediction are dropped (where applicable).
      3. The predictions are filtered by a user-specified confidence threshold.
         Any prediction below this threshold is dropped.
    Setting conf_threshold=0.0 would skip the filtering of predictions, while
    preserving the other memory-saving features.
    Inputs:
    - session: the aiohttp.ClientSession object used to make the POST request
    - url: the URL of the TensorFlow Serving server
    - batch: the image chip batch to be submitted as a numpy array of
      dimension (num_chips, height, width, channels)
    - i: the current chip index (needed to reassemble the predictions)
    - results: a Python dictionary into which results are appended in form of:
      {[i]: {['detection_score']:[...],
              ['detection_class']:[...],
              ['detection_bbox']:[...]},
        ...}
    - conf_threshold (optional, default=0.0): the confidence threshold to
      use for filtering predictions (0.0 to 1.0).
    Returns:
     - NONE (but the results dictionary is updated with each chip's inference results)
    """

    conf_threshold = float(raw_conf_threshold)
    async with session.post(
        url, json={"signature_name": "serving_default", "instances": batch.tolist()}
    ) as resp:
        pred = await resp.json()

        if "predictions" in pred:
            cats = pred["predictions"][0]

            # filter the predictions based on confidence score
            # (and drop the dtypes to save memory)
            scores_np = np.array(cats["detection_scores"], dtype=np.float16)
            filtered_scores = scores_np[scores_np >= conf_threshold].tolist()

            if len(filtered_scores) > 0:
                print(
                    f"{i} has {len(filtered_scores)} predictions above \
                    confidence threshold of {conf_threshold}."
                )

                formatted_prediction = {}
                filtered_classes = (
                    np.array(cats["detection_classes"])[scores_np >= conf_threshold]
                    .astype("uint8")
                    .tolist()
                )
                # print(f"{i}: filtered classes: {len(filtered_classes)}")

                filtered_bboxes = np.array(cats["detection_boxes"])[
                    scores_np >= conf_threshold
                ].tolist()

                # print(f"{i}: filtered bboxes: {len(filtered_bboxes)}")

                formatted_prediction["detection_scores"] = filtered_scores
                formatted_prediction["detection_classes"] = filtered_classes
                formatted_prediction["detection_boxes"] = filtered_bboxes
                results[i] = formatted_prediction

            else:
                print(
                    f"{i} had predictions, but they were all below \
                    the confidence threshold of {conf_threshold}."
                )
        else:
            print(f"No predictions at all for {i}.")
            print(f"{i}: {pred['error']}")


async def batch_inference(instances, tf_serving_url, conf_threshold, concurrency=1):
    """An async function for performing client-side batch inference on a set of
    image chips.
    Concurrency controls how many image chips are provided to the Tensorflow Server
    per HTTP post request (client-side batching). This value should not exceed the
    num_batch_threads setting in the Tensorflow Server batch.config file. In turn,
    the num_batch_threads setting should match the number of threads on your CPU
    (or GPU for GPU-based inference). This combination of client-side and server-side
    batching should result in the best performance.
    NOTE: If concurrency is set to 1, the client-side batching is effectively
    disabled. Each image chip is submitted individually, and only server-side
    batching will be enabled. For the time being (3/25/2022) I am leaving '1'
    as the default, so the API by default submits 1 image chip per HTTP post request,
    and TF Serving handles batching on the server-side. The concurrency variable
    is being left in place for future experimentation with combo client-side and
    server-side batching.
    Inputs:
    - instances: a "chipped" set of images given as a numpy array of shape:
        (num_chips, height, width, channels).
    - concurrency: the number of batches to split the numpy array into to
        provide as concurrent requests to the TensorFlow Serving server.
        As of 3/25/2022, this value is a placeholder and should be set to 1.
     Outputs:
    - predictions: a dictionary containing the raw, multi-class object detection
        inference results for the current batch of chips.
    """

    num_batches = math.ceil(len(instances) / concurrency)
    print(f"Number of batches: {num_batches}")
    batches = np.array_split(instances, num_batches)

    conf_thresh_flt = float(conf_threshold / 100)

    predictions = {}
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(
            *[
                _async_post(
                    session, tf_serving_url, batches[i], i, predictions, conf_thresh_flt
                )
                for i in range(len(batches))
            ]
        )

    return predictions


def prep_sensor_params(supported_sensors, selected_sensor):
    """A simple function designed to load the selected sensor parameters from a JSON
    file.
    """
    sensor_params = (
            float(supported_sensors[selected_sensor]['focal_length_mm']),
            float(supported_sensors[selected_sensor]['sensor_height_cm']),
            float(supported_sensors[selected_sensor]['sensor_width_cm']),
    )

    return sensor_params


def json_keys_to_int(x):
    return {int(k): v for k, v in x.items()}


def calc_max_gsd(
    flight_agl_meters, image_height, image_width, sensor_params
):
    """A simple function that esitmates the ground spacing distance (GSD) of
    non-georeferenced aerial photographs. Both the GSD in the Y and X dimensions
    are computed, and the max is returned from those.

    Parameters:
    - flight_agl_meters: a float (decimal) or integer value representing the sensor's
        height above ground level (AGL) at the time of image acquisition. Units are
        required to be meters.
    - image_height, image_width: Integer values representing the height and width of the
        image in pixels
    - sensor_params: a dictionary containing the sensor parameters for the current
        image. The dictionary should the sensor name as key. The value should be the
        focal length (mm), sensor height (cm) and sensor width (cm) in a list.

    Returns:
    - max_gsd: An float value reprenting the maximum GSD of the image in meters.
    """
    sensor_focal_length_mm = float(sensor_params[0])
    sensor_height_cm = float(sensor_params[1])
    sensor_width_cm = float(sensor_params[2])

    flight_agl_cm = flight_agl_meters * 1000

    gsd_h = (flight_agl_cm * sensor_height_cm) / (sensor_focal_length_mm * image_height)
    gsd_w = (flight_agl_cm * sensor_width_cm) / (sensor_focal_length_mm * image_width)

    max_gsd = max(gsd_h, gsd_w)

    return max_gsd


def resize_to_gsd(input_image, estimated_gsd_cm, target_gsd_cm):
    """A simple function that computes a scaling factor between the non-georeferenced
    input image's estimated GSD and the project's target GSD and applies the computed
    scaling factor to the original image. The result is a resampled image with GSD
    matching this project's target of 2.0cm.
    Inputs:
    - input_image: A 3-band PIL Image.Image. This is generally expected to have been
        generated by the ingest_image() function.
    - estimated_gsd_cm: The input_image's estimated ground spacing distance (GSD)
        in centimeters. This value is generally expected to have been computed by
        the calc_gsd() function.
    - target_gsd_cm: The project's target ground spacing distance (GSD). The output
        image will be reampled to this GSD. This value defaults to the project's
        target GSD of 2.0 cm.
    Returns:
    - new_im: A resampled PIL Image.Image object.
    """

    upscale_factor = (estimated_gsd_cm - float(target_gsd_cm)) / float(target_gsd_cm)

    output_width = int(input_image.width + (input_image.width * upscale_factor))
    output_height = int(input_image.height + (input_image.height * upscale_factor))
    new_size = (output_width, output_height)

    new_im = input_image.resize(new_size)

    return new_im


def _denormalize_coordinates(bbox, im_height, im_width):
    """A simple funtion that takes normalized bounding box image coordinates (0-1.0)
    and converts to absolute image pixel coordinates. These bounding boxes should have
    Tensorflow's preferred coordinate order of (ymin, xmin, ymax, xmax). The return
    coordinates are in the same order.

    Inputs:
    - bbox: A list of floats representing the normalized bounding box coordinates.
        This list should be in the coord. order of (ymin, xmin, ymax, xmax).
    - im_height: An integer representing the image height in pixels.
    - im_width: An integer representing the image width in pixels.

    Returns:
    px_coords: A list of floats representing the absolute bounding box coordinates.
        Coord order: (ymin, xmin, ymax, xmax).
    """

    # this is set to Tensorflow Object Detection ordering (ymin, xmin, ymax, xmax)
    ymin = bbox[0]
    xmin = bbox[1]
    ymax = bbox[2]
    xmax = bbox[3]

    top = int(ymin * im_height)
    left = int(xmin * im_width)
    bottom = int(ymax * im_height)
    right = int(xmax * im_width)

    px_coords = [top, left, bottom, right]
    # print("ymin, xmin, ymax, xmax")
    # print(f"norm: {bbox}, denorm {px_coords}")

    return px_coords


def read_tf_label_map(label_map_path):
    """Reads a Tensorflow Object Detection API label map from a pbtxt file without
    the need for TF/protobuf libraries. Returns a simple mapping of class_id (int)
    to class_name (string) in a Python dictionary.

    NOTE: This function is strictly dependent on TF's label map format, (the 'item',
        'id:' and 'name:' fields are hardcoded).

    All credit to the original author:
      https://stackoverflow.com/questions/55218726/how-to-open-pbtxt-file

    INPUTS:
      - label_map_path: The path to the label map .pbtxt file.

    OUTPUTS:
      - A Python dictionary with class_id:class_name mappings of types
        (int:string)
    """

    item_id = None
    item_name = None
    items = {}

    print(label_map_path)
    with open(label_map_path, "r") as label_map_file:
        for line in label_map_file:
            line.replace(" ", "")
            if line == "item{":
                pass
            elif line == "}":
                pass
            elif "id:" in line:
                item_id = int(line.split(":", 1)[1].strip())
            elif "name:" in line:
                item_name = line.split(":", 1)[1].replace("'", "").strip()

            if item_id is not None and item_name is not None:
                items[item_id] = item_name
                item_id = None
                item_name = None

    return items


def results_dict_to_dataframe(image_name, orig_results, label_map):
    """This functions converts the results dictionary into a Pandas DataFrame.
    The dataframe is formatted with additional fields and pretty column
    headers. The intention is to save this DF to a CSV file for later use.
    Inputs:
    - image_name: A string representing the image's filename (no extension).
    - orig_results: A dictionary containing inference results for the image.
        This is most likely coming from reassemble_chip_results().
    - label_map: A dictionary mapping the class ID (int) to the class name (str).
    """
    # working on a copy
    results = orig_results.copy()

    # split the bbox coordinates to individual lists (columns).
    bbox_array = np.array(results["bboxes"], dtype=np.uint8)
    ymin = bbox_array[:, 0].tolist()
    xmin = bbox_array[:, 1].tolist()
    ymax = bbox_array[:, 2].tolist()
    xmax = bbox_array[:, 3].tolist()

    results["ymin"] = ymin
    results["xmin"] = xmin
    results["ymax"] = ymax
    results["xmax"] = xmax

    # get the filename list (column) together.
    filenames = [image_name] * len(results["classes"])
    results["filename"] = filenames

    # create a pandas dataframe.
    raw_df = pd.DataFrame.from_dict(results)

    # add a class name column. the .astype() is because the label_map dict gets crushed
    # to all strings when passed from FastAPI to the Celery worker.
    raw_df["class_name"] = raw_df["classes"].astype("string")
    raw_df.replace({"class_name": label_map}, inplace=True)

    # beautify!
    raw_df["class_id"] = raw_df["classes"]
    raw_df["score"] = raw_df["scores"]

    ordered_df = raw_df[
        ["filename", "class_name", "class_id", "score", "ymin", "xmin", "ymax", "xmax"]
    ]

    return ordered_df


def plot_bboxes_on_image(image_path, labels, color_ramp, class_scheme, thickness=4):
    """A custom function to plot object detection bounding boxes on an image.
    This function is pretty basic. The only motivation to writing this was to
    remove the need for TF Object Detection API's heavy dependencies within the
    Celery geoprocessor.

    Inputs:
    - image_path: A string representing the path to the image to be plotted.
    - labels: A dictionary which contains the keys "bboxes", "scores", and "classes".
        Each key's value should be a list of values for each bbox. This is most likely
        coming from reassemble_chip_results().
    - color_ramp: A list of colors to use for the bounding boxes.
    - class_scheme: A dictionary mapping the class ID (int) to the class name (str).
    - thickness: An integer representing the thickness of the bounding box lines.
        Default is 4.
    Returns:
    - pil_im: the plotted image as a PIL Image.Image object.
    """

    with Image.open(image_path, "r") as pil_im:
        im_width, im_height = pil_im.size
        print(f"Image size: {im_width}, {im_height}")

        draw = ImageDraw.Draw(pil_im)

        for i, bbox in enumerate(labels["bboxes"]):
            # PIL uses a top-left origin (0, 0)
            bottom, left, top, right = bbox

            bbox_class = labels["classes"][i]
            bbox_score = labels["scores"][i]

            bbox_color = color_ramp[bbox_class]
            bbox_label = class_scheme[bbox_class]

            if thickness > 0:
                draw.rectangle(
                    [(left, top), (right, bottom)], width=thickness, outline=bbox_color
                )
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except IOError:
                font = ImageFont.load_default()

            display_string = f"{bbox_label}, {format(bbox_score, '.2f')}"

            # box for display string
            text_width, text_height = font.getsize(display_string)
            margin = np.ceil(0.05 * text_height)
            draw.rectangle(
                [
                    (left - margin, top),
                    (left + text_width + margin, top + text_height + margin),
                ],
                fill=bbox_color,
            )

            draw.text((left, top), display_string, fill="black", font=font)

        return pil_im


def collate_per_image_results(in_dir):
    """This function collates the per-image inference results into merged
    results for the entire user submission.
    All CSVs are merged via Pandas (for writing to CSV). Along the way we
    tally each debris type and the cumulative sum of all debris types, which
    is written as the final row of a final_counts dataframe (for writing to
    CSV).

    TODO: Bundle JSONS?
    Inputs:
    - in_dir: A string representing the path to the directory containing the
        per-image inference results.
    Returns:
    - final_df: A Pandas DataFrame containing the merged CSV results.
    - final_counts: A pandas dataframe containing two columns which correspond
        to the debris type and the number of debris of that type respectively.
        The total debris (sum) is also included as the bottom row.
    """
    # scan directory for CSV files
    csvs = [join(in_dir, x) for x in listdir(in_dir) if x.endswith(".csv")]

    # stack all CSVs into a single dataframe.
    dfs = []
    for target_csv in csvs:
        target_df = pd.read_csv(target_csv)
        dfs.append(target_df)
    final_df = pd.concat(dfs, ignore_index=True)

    # from that single dataframe, count occurences of debris across all images,
    # sum the total, append the total, and prep a Pandas series for export to a CSV.
    debris_counts = final_df["class_name"].value_counts()
    debris_total = pd.Series(debris_counts.sum(), index=["total debris (sum)"])

    counts = []
    counts.append(debris_counts)
    counts.append(debris_total)
    final_counts = pd.concat(counts)

    return final_df, final_counts
