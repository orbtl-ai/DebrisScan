# DebrisScan


## Introduction
DebrisScan is a web-based app for automatically counting marine debris in your aerial
images (typically collected from drones). The app is designed to be flexible and
user-friendly. Further, DebrisScan and it's underlying technologies are completely free
and open source; eliminating startu costs and lowering the barriers of entry for
researchers and citizen scientists alike to begin applying AI worflows to the
measurement and management of marine debris.

![An image showing AI detections of plastic, wood, and other manmade marine debris
along a complex shoreline image. The AI detections are made with boxes drawn around
each object that are color-coded by type.](https://github.com/orbtl-ai/DebrisScan/blob/main/static/debrisscan_example.png)

## Key Features
1. A complete, free, and open source environment for training and deploying deep
    learning-based object detection models.
2. State-of-the-art computer vision models fine-tuned for the automatic detection of
    shoreline stranded marine debris from aerial images.
3. A user friendly interface for interacting with the object detection models.
4. A powerful and well-documented backend REST API for automating bulk uploads or
    integrating DebrisScan into existing apps, software, or workflows.
5. Detailed standing stock debris survey reports, maps, plots, and metadata to help
    understand shoreline debris accumulation and allow multi-date or multi-site comparison.

## Computer Vision Models
WARNING: Models are provided as-is. No warranty or accuracy is expressed or implied.

This repo is not explicitly designed to host or distribute pre-trained computer vision
models for marine debris. However, this repo does does contain an `app/tf_server/models/`
folder which contains the following models:

### efficientdet-d0 *(default)*
An EfficientDet-d0 object detection model from the [Tensorflow Object Detection Model
Zoo](https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/tf2_detection_zoo.md)
that was fine-tuned with a labeled marine debris data set. This is the default model
used by DebrisScan as it has been found to offer competitive performance with larger
models while being fast enough for CPU-based inference.

## Quick Start *(Local Installation)*
Installing and deploying DebrisScan is very simple, and can be executed in XX steps for
basic installation on your local system. However, users of DebrisScan should at least have
basic familiarity with the command line, git, and preferably Docker too (optional).

> **Note**
> DebrisScan officially supports Windows 11 and Linux systems (AMD64 only). Windows 10
> Intel-based MacOS systems may work but are not officially supported (see Warnings below).

> **Warning**
> DebrisScan will install and run on Windows 10 using the steps below, **but only when
> utilizing a CPU.** Utilizing Docker with a GPU requires extra configuration steps
> [See this link for more information](https://www.docker.com/blog/wsl-2-gpu-support-for-docker-desktop-on-nvidia-gpus/).

> **Warning**
> DebrisScan does not officially support *any* ARM-based systems (e.g., Apple Silicon,
> Raspberry Pi, etc.).

### Step 1: Install Neccecary Software Dependencies
DebrisScan is designed to deploy simply on a wide range of operating systems and hardware
configurations, ranging from your laptop to a high-capacity cloud computer. To
accomplish these goals we distribute the DebrisScan's app codebase via GitHub (you are here!)
and use [Docker](https://www.docker.com/) to install DebrisScan and all of it's
necessary software dependencies.

#### Git
To install Git, [follow the instructions for your operating system here](https://git-scm.com/downloads).

#### Docker
To install Docker, [follow the instructions for your operating here](https://www.docker.com/products/docker-desktop/).

### Step 2: Download this Repo with Git
To download the codebase you need to "clone" this repo to your local computer with
the following command:
```bash
git clone https://github.com/orbtl-ai/DebrisScan.git
```

### Step 3: Build and Run DebrisScan with Docker
Once downloaded, navigate into the DebrisScan folder and execute the following command:
```bash
docker compose up --build
```
> **Note**
> The first time you run this command it will take a while to download and install all
> of the necessary software dependencies. However, subsequent runs will be much faster.

> **Note**
>The `--build` flag is only needed the first time you run this command.

### Step 4: Access DebrisScan in your Browser
#### Upload Data and Begin Processing
Once the Docker containers are running, the DebrisScan interface can be accessed by
opening your favorite web browser and navigating to the following URL:
`http://localhost:8080/`.

- INSERT PIC HERE!!!!

#### Check Processing Status
- Status Tab
- Flower Admin

#### Retrieve and View Results
- Status Tab

#### View DebrisScan's Backend API Documentation (Optional)

#### View DebrisScan's Admin Dashboard (Optional)

## Advanced Documentation
**UNDER CONSTRUCTION!!**

## Credits
DebrisScan was developed by [ORBTL AI](https://orbtl.ai) with funding and support from
the [NOAA's National Centers for Coastal Ocean Science](https://coastalscience.noaa.gov/),
[Oregon State University](https://oregonstate.edu), and
[NOAA's Marine Debris Program](https://marinedebris.noaa.gov/). DebrisScan is a single
component of a larger effort to operationalize advanced technologies for the measurement
and management of marine debris. For more information on the project, please visit the
[project's homepage](https://coastalscience.noaa.gov/project/using-unmanned-aircraft-systems-machine-learning-and-polarimetric-imaging-to-develop-a-system-for-enhanced-marine-debris-detection-and-removal/).

## Contact
For more information on DebrisScan, please contact [ORBTL AI](https://orbtl.ai/contact-us/).
