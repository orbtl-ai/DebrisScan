<h1>🌊🥤 DebrisScan: Automatically Scan Drone Imagery for Marine Debris — Using AI 
🤖📸</h1> 

## Introduction
DebrisScan is a web-based app for automatically identifying marine debris in 
your aerial images (typically collected from drones). The app is designed to be 
flexible and user-friendly. Further, DebrisScan and its underlying technologies 
are completely free and open source, eliminating startup costs and lowering the 
barriers of entry for researchers and citizen scientists alike to begin 
applying AI workflows to the measurement and management of marine debris.

![An image showing AI detections of plastic, wood, and other manmade marine 
debris along a complex shoreline image. The AI detections are made with boxes 
drawn around each object that are color-coded by 
type.](static/debrisscan_example.png)

DebrisScan is a single component of a larger effort to operationalize advanced 
technology for measurement and management of marine debris. For more 
information on this larger effort and its partners, please visit the [project's 
homepage][project homepage].

[project homepage]: https://coastalscience.noaa.gov/project/using-unmanned-aircraft-systems-machine-learning-and-polarimetric-imaging-to-develop-a-system-for-enhanced-marine-debris-detection-and-removal/


## Key Features
1. A complete, free, and open source environment for training and deploying 
deep learning-based object detection models.
1. State-of-the-art computer vision models fine-tuned for the automatic 
detection of shoreline stranded marine debris from aerial images.
1. A user friendly interface for interacting with the object detection models.
1. A powerful and well-documented backend REST API for automating bulk uploads 
or integrating DebrisScan into existing apps, software, or workflows.
1. Detailed standing stock debris survey reports, maps, plots, and metadata to 
help understand shoreline debris accumulation and allow multi-date or multi-
site comparison.


## Quick Start *(Local Installation)*
Installing and deploying DebrisScan is very simple, and can be executed in a 
few easy steps for basic installation on your local system. However, users of 
DebrisScan should at least have basic familiarity with the command line, Git, 
and preferably Docker too (optional).

> **Note**
> DebrisScan officially supports Windows 11 and Linux systems (AMD64 only). 
> Windows 10 and > Intel-based MacOS systems may work, but are not officially 
> supported (see Warnings below).

> **Warning**
> DebrisScan will install and run on Windows 10 using the steps below, **but 
> only when utilizing a CPU.** Utilizing Docker with a GPU requires extra 
> configuration steps. [See this link for more information][Docker info].
> 
> [Docker info]: https://www.docker.com/blog/wsl-2-gpu-support-for-docker-desktop-on-nvidia-gpus/

> **Warning** 
> DebrisScan does not officially support *any* ARM-based systems (e.g., Apple 
> Silicon, Raspberry Pi, etc.).


### Step 1: Install Necessary Software Dependencies
DebrisScan is designed to deploy simply on a wide range of operating systems 
and hardware configurations, ranging from your laptop to a high-capacity cloud 
computer. To accomplish these goals we distribute DebrisScan's codebase via 
GitHub (you are here!) and use [Docker](https://www.docker.com/) to install all 
of DebrisScan's necessary software dependencies.


#### Git
To install Git, [follow the instructions for your operating system 
here](https://git-scm.com/downloads).


#### Docker
To install Docker, [follow the instructions for your operating system 
here](https://www.docker.com/products/docker-desktop/).


### Step 2: Download this Repo with Git
To download the DebrisScan codebase you need to "clone" this repo to your local 
computer with the following command:
```bash
git clone https://github.com/orbtl-ai/DebrisScan.git
```


### Step 3: Build and Run DebrisScan with Docker
Once downloaded, navigate into the `DebrisScan/` folder and execute the 
following command from the root directory to simultaneously download the needed 
software dependencies, build, configure, and run the entire app:
```bash
docker compose up --build
```
> **Note**
> The first time you run this command it will take a while to download and 
> install all of the necessary software dependencies. However, subsequent runs 
> will be much faster.


### Step 4: Access DebrisScan in your Browser

#### Upload Data and Begin Processing
Once the Docker containers are running, the DebrisScan interface can be 
accessed by opening your favorite web browser and navigating to the following 
URL:`http://localhost:8080/`.

![An image showing DebrisScan's Job Upload tab, which has multiple text boxes 
and slider bars that allow users to configure DebrisScan's settings.](static/debrisscan_v05_example.png)

There are two tabs in the DebrisScan interface: `Job Upload` and `Job 
Status/Results`. By default, the app launches on the `Job Upload` tab, which is 
shown in the image above.


### Step 5: Job Upload
The `Job Upload` tab allows users to upload batches of aerial images for AI 
processing. Optionally, users can also provide additional information about 
flight altitude, camera, and/or drone model, which will allow DebrisScan to 
resample the imagery to match the AI's optimal resolution, increasing
performance and accuracy.

> **Warning**
> DebrisScan's current models were trained on aerial imagery with a ground 
> spacing distance (GSD) of 2cm, and performance decreases as the uploaded 
> imagery's GSD diverges. It is generally recommended for users to opt-in to 
> `Optional Resampling`, which can infer image GSD from user-provided `Flight 
> Altitude` and `Sensor` information.

Further, users can adjust the `Confidence Threshold` slider to adjust the 
minimum confidence threshold for an AI prediction to be kept in the final 
results. The default value for this slider is "40%" (on a scale of 0-100% 
confidence), but this value can be adjusted to either allow more or less model 
predictions. A value of "0%" will keep all AI predictions, while a value of 
"100%" will keep almost no predictions.

> **Note**
> Increasing the `Confidence Threshold` slider is useful for filtering out 
> false positives (i.e., AI predictions that are not actually marine debris). 
> However, it is important to note that this comes with the trade-off of 
> potentially filtering actual marine debris, which often results in a higher 
> rate of false negatives (i.e., actual marine debris that is not detected by 
> the AI). It is often useful to experiment with the `Confidence Threshold` 
> slider to find balance.

The user will be prompted if the job was submitted successfully and provided 
with a unique `Job ID` number that allows the job's status or results to be 
retrieved by returning to the `Job Status/Results` tab at any point in the 
future and providing the `Job ID` number.


#### Check Job's Processing Status
The `Job Status/Results` tab will allow you to return to the DebrisScan 
interface at any time in the future to check the status of your job or retrieve 
the results of your job using the `Job ID` provided during the `Job Upload` 
step. This is useful to prevent the user from waiting around for the AI to 
finish counting debris!

![An image showing DebrisScan's `Job Status/Results` tab, in which a two text 
boxes sit atop one another. The top box takes a user's job ID as input, and the 
bottom box returns information or files related to the 
job.](static/debrisscan_v05_status_example.png)


#### Download Job's Results
Once DebrisScan has completed processing your job, the `Job Status/Results` tab 
will both display this status and return a zip file of your results. The zip 
file will contain the original images you uploaded, but with the AI's 
predictions drawn on the image and labeled by debris type and prediction 
confidence. Additionally, CSV and JSON reports will be delivered.

Congrats! You have successfully installed and deployed DebrisScan on your local 
system.


## Advanced Documentation *(UNDER CONSTRUCTION!!)*

### View DebrisScan's Admin Dashboard (Optional)
By default, DebrisScan will launch an Administrative Dashboard powered by 
Flower. This allows the user to view/control various aspects of the app's 
backend job processing queue, results store, and the jobs themselves. This 
dashboard can be accessed on your local machine by navigating to the following 
URL: `http://localhost:5555/`.

![An image showing DebrisScan's Administrative Dashboard with tabs to view 
worker, brokers, and tasks.](static/flower_example.png)


## Computer Vision Models
WARNING: Models are provided as-is. No warranty or accuracy is expressed or 
implied.

This repo is not explicitly designed to host or distribute pre-trained computer 
vision models for marine debris. However, this repo does does contain an 
`app/tf_server/models/` folder which contains the following models:


### efficientdet-d0 *(default)*
An EfficientDet-d0 object detection model from the [Tensorflow Object Detection Model
Zoo](https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/tf2_detection_zoo.md)
that was fine-tuned with a labeled marine debris data set. This is the default 
model used by DebrisScan as it has been found to offer competitive performance 
with larger models while being fast enough for CPU-based inference.


## License
DebrisScan is licensed under the Apache License 2.0 found in the LICENSE file 
in the root directory of this repository.


## Credits
DebrisScan is presented as a free, open source software under funding and support from
[NOAA's National Centers for Coastal Ocean Science](https://coastalscience.noaa.gov/),
[Oregon State University](https://oregonstate.edu), and
[NOAA's Marine Debris Program](https://marinedebris.noaa.gov/).

DebrisScan is developed and maintained by [ORBTL AI](https://orbtl.ai).


## Contact
For more information about DebrisScan itself, please [contact ORBTL AI](https://orbtl.ai/contact/).
