""" This module spins up the main Gradio/FastAPI web app."""

from os import getenv
from os.path import join
import json
import uuid

import asyncio
import aiofiles

from celery import states
from celery.result import AsyncResult

import gradio as gr

from client.client_utils import (
    save_tmp_with_pil,
    async_dump_user_submission_to_json,
)
from geoprocessor.tasks import celery_app
from configs.api_config import api_configs


APP_DATA = getenv("DOCKER_APP_DATA", "/app_data")

supported_sensors = json.load(open(api_configs.SUPPORTED_SENSORS_JSON, "r"))


async def async_object_detection(
    aerial_images, resample, flight_agl, sensor_platform, confidence_threshold
):
    """
    An async function that receives a user upload via Gradio, saves the imagery
    and user submission to a working directory, and forwards the CPU- and GPU-intensive
    processing to a Celery worker.

    Parameters:
    - aerial_images: A list of NamedTemporaryFiles supplied by the user via Gradio's
        input "File" component.
    - resample: A boolean indicating whether the user wants to resample their imagery
        to match the detection model's target GSD.
    - flight_agl: A float representing the user's flight altitude above ground level
        in meters.
    - sensor_platform: A string representing the user's UAV platform or camera model.
        Used to derive sensor-specific parameters for resampling.
    - confidence_threshold: A float representing the minimum confidence threshold at
        which the model's detections are kept.

    Returns:
    - A dictionary containing the following:
        - upload_results: A gr.update() which toggles the visibility of Gradio's
            output "Text" component for displaying the below...
        - out_payload: The unique UUID4 task_id associated with the Celery task.
        - out_message: A string message written to inform the user of the task's status,
            next steps, success, warnings, errors, etc.
    """
    # Create a unique task id that will follow this job from start-to-finish
    task_id = str(uuid.uuid4())
    print(f"Initizalizing task {task_id}...")

    task_path = join(APP_DATA, task_id)
    await aiofiles.os.mkdir(task_path)

    loop = asyncio.get_running_loop()

    # Utilize asyncio for the IO-bound tasks
    task_path = await loop.run_in_executor(
        None, save_tmp_with_pil, task_path, aerial_images
    )

    await async_dump_user_submission_to_json(
        task_id, task_path, aerial_images, resample, flight_agl, sensor_platform,
        confidence_threshold,
    )

    # Celery task queue for the CPU-bound tasks
    celery_app.send_task(
        "object_detection",
        args=[task_path],
        task_id=task_id,
    )

    print(f"Task {task_id} complete and sent to Celery.")

    out_msg = (
        "Upload Successful! It may take our robots awhile to count all those debris, "
        "so you shouldn't wait around for them! Please save your Job ID (above) and "
        "return later to retrieve your results at the 'Retrive Results' tab above!"
    )

    return {
        upload_results: gr.update(visible=True),
        out_payload: str(task_id),
        out_message: out_msg
    }


async def get_task_status(task_id):
    """This function returns the status of a Celery task when provided with a task_id.
    The task_id is provided in the URL as a path parameter.

    Inputs:
    - task_id: A string representation of a unique task_id associated with a
        Celery task.

    Returns:
    - JSONResponse with information about the job's status, errors, and/or results.
    """

    result = AsyncResult(task_id, app=celery_app)

    result_state = str(result.state)
    result_error = str(result.info) if result.failed() else None

    # result.get() can block the whole thread if nothing is there... use with caution
    result_file = str(result.get()) if result.state == states.SUCCESS else None

    if result_error is None and result_state == "PENDING":
        out_message = (
            "PENDING: Your submission has been received and is currently waiting in a "
            "queue for processing. Please check back later."
        )

        return {
            out_status: gr.update(value=out_message, visible=True),
            out_file: gr.update(visible=False),
        }

    elif result_error is None and result_state == "STARTED":
        out_message = (
            "STARTED: Your submission is currently being processed! "
            "Please check back later."
        )

        return {
            out_status: gr.update(value=out_message, visible=True),
            out_file: gr.update(visible=False),
        }

    elif result_error is None and result_state == "SUCCESS":
        out_message = (
            "SUCCESS: Your submission has been processed successfully! "
            "Please click the 'Download Results' button to the right to "
            "download your results."
        )

        return {
            out_status: gr.update(value=out_message, visible=True),
            out_file: gr.update(value=result_file, visible=True),
        }

    elif result_error is not None:
        out_message = f"{result.id} HAS FAILED!. {str(result_error)}."

        return {
            out_status: gr.update(value=out_message, visible=True),
            out_file: gr.update(visible=False),
        }

    else:
        out_message = (
            f"{result.id}'s job status can not be retrieved reliably... "
            "please contact the project's administrators."
        )

        return {
            out_status: gr.update(value=out_message, visible=True),
            out_file: gr.update(visible=False),
        }


def toggle_resampling(choice):
    if choice == "False":
        return {
            in_flight_agl: gr.update(
                visible=False, value=76
            ),
            in_sensor_platform: gr.update(
                visible=False, value=list(supported_sensors.keys())[0],
            )
        }
    elif choice is True:
        return {
            in_flight_agl: gr.update(
                visible=True, value=76
            ),
            in_sensor_platform: gr.update(
                visible=True, value=list(supported_sensors.keys())[0],
            ),
        }
    else:
        return {
            in_flight_agl: gr.update(visible=False),
            in_sensor_platform: gr.update(visible=False),
        }


browser_title = "DebrisScan Demo"

md_title = """
    #  Welcome to DebrisScan
    # 🌊🥤 (*DEMO v0.05*) 📸 🤖
"""

md_description = """
    **DebrisScan API is an app that automatically detects, classifies, and measures
    shoreline-stranded marine debris from aerial images. This demo allows you to upload
    your own aerial images (typically taken from a drone or aircraft) to be scanned for
    marine debris by our cutting-edge AI!**
"""


# generate an html block with white background and three images in a row
html_images = """
    <div style="background-color:white; padding: 10px; border-radius: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <img src="http://orbtl.ai/wp-content/uploads/2022/09/orbtl_black_txtOnly_largeBorder.jpg?raw=true" width="30%" />
            <img src="https://oceanservice.noaa.gov/facts/noaa-emblem-rgb-2022.png?raw=true" width="20%" />
            <img src="https://communications.oregonstate.edu/sites/communications.oregonstate.edu/files/osu-primarylogo-2-compressor.jpg?raw=true" width="30%" />
        </div>
    </div>
"""


md_article = """
    DebrisScan was developed by [ORBTL AI](https://orbtl.ai) with partnership and
    funding from [Oregon State University](https://oregonstate.edu/),
    [NOAA's National Centers for Coastal Ocean Science](https://coastalscience.noaa.gov/),
    and [NOAA's Marine Debris Program](https://marinedebris.noaa.gov/).
"""


md_footer = """
    For more information about DebrisScan, please visit the following links: [NOAA NCCOS Project Homepage](https://coastalscience.noaa.gov/project/using-unmanned-aircraft-systems-machine-learning-and-polarimetric-imaging-to-develop-a-system-for-enhanced-marine-debris-detection-and-removal/) | [DebrisScan's Open GitHub Repo](https://github.com/orbtl-ai/debrisscan)
"""


with gr.Blocks(title=browser_title) as demo:
    gr.Markdown(md_title)
    gr.Markdown(md_description)

    with gr.Tab("Job Upload"):
        with gr.Row():
            with gr.Column():
                gr.Markdown("## 🗾 Aerial Image Upload")
                in_aerial_images = gr.File(
                    label="Aerial Image Upload",
                    file_count="multiple",
                )
                gr.Markdown("## 🎛 Optional Settings")
                with gr.Column():
                    gr.Markdown("""
                        ### ⚙️ Automatically resample your aerial images to match our AI's expected resolution?
                        *This procedure requires us to know more about your imagery,
                        but it should improve your detection results by ensuring your
                        aerial image resolution matches the image resolution used to
                        train our AIs (they can be a little picky- so this is HIGHLY
                        RECOMMENDED).*
                    """)
                    in_resampling = gr.Checkbox(
                            label=f"Auto-downsample your imagery to \
                                {int(api_configs.TARGET_GSD_CM)}cm resolution?"
                    )
                    in_flight_agl = gr.Slider(
                        label="Flying Height Above Ground Level (meters)",
                        minimum=3,
                        maximum=122,
                        value=76,
                        step=1,
                        visible=False,
                    )
                    in_sensor_platform = gr.Dropdown(
                        label="Sensor Platform",
                        choices=list(supported_sensors.keys()),
                        value=list(supported_sensors.keys())[0],
                        visible=False,
                    )
                    in_resampling.change(
                        fn=toggle_resampling,
                        inputs=in_resampling,
                        outputs=[in_flight_agl, in_sensor_platform],
                    )

                with gr.Column():
                    gr.Markdown("""
                        ### ⚙️ Modify Confidence Threshold?
                        *Our detectors assign each detection a
                        'confidence score'. This setting filters all detections whose
                        confidence score is below the threshold. Lowering the threshold
                        allows in more detections, biasing the results toward a higher
                        rate of false positive detections. Conversely, increasing the
                        threshold filters the most uncertain detections, biasing the
                        results towards a higher rate of false negative detections.
                        (RECOMMENDED DEFAULT VALUE: 30%)*
                    """)
                    confidence_threshold = gr.Slider(
                        label="Confidence Threshold (%)",
                        minimum=0,
                        maximum=100,
                        value=api_configs.CONFIDENCE_THRESHOLD,
                        step=5,
                    )
                submit_button = gr.Button(value="Upload Job")

            with gr.Column(visible=False) as upload_results:
                gr.Markdown("## Upload Results")
                out_payload = gr.Text(label="Job ID")
                out_message = gr.Text(label="Message")

            submit_button.click(
                async_object_detection,
                inputs=[
                    in_aerial_images,
                    in_resampling,
                    in_flight_agl,
                    in_sensor_platform,
                    confidence_threshold,
                ],
                outputs=[upload_results, out_payload, out_message],
            )

    with gr.Tab("Job Status/Results"):
        gr.Markdown("## 🧾 Enter Job ID")
        with gr.Column():
            in_task_id = gr.Text(label="Job ID", show_label=False)
            status_button = gr.Button(value="Get Job Status")

        gr.Markdown("## ⏱ Job Status")
        with gr.Row():
            out_status = gr.Text(
                label="Job Status",
                show_label=False,
                value="Awaiting Job ID above...",
            )
            out_file = gr.File(
                label="Download your Results!",
                value=None,
                visible=False,
            )
        status_button.click(
            get_task_status,
            inputs=[in_task_id],
            outputs=[out_status, out_file],
        )

    gr.Markdown(md_article)
    gr.HTML(html_images)
    gr.Markdown(md_footer)


# gr.close_all()
demo.queue(concurrency_count=1)
demo.launch(server_name="0.0.0.0", server_port=8080)
