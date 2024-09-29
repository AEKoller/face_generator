# Extempo Face Generator Guide

### Purpose
This repo contains two scripts designed to interface with [Extempo's](https://www.extempo.rocks/) StyleGan2 face generator API. Each script interacts with the API in different ways, however, each operate along the following paramaters: 
1. A random image is generated
2. The predictions for that randomly generated image are returned
3. The random image is transformed based on a chosen characteristic and a beta
    - Beta is an integer value representing a degree of standard deviation from the mean. e.g. -2 would represent two standard deviations below the mean, and 3 would represent three standard deviations above the mean.
4. The transformed image(s) is/are returned, along with a text file containing relevant information regarding the transformed picture

<br>

The two scripts, `main.py` and `selector.py` interact with the API in slightly different ways:

<br>

`main.py`

Takes a characteristic and a set of betas to generate multiple images based on a list of betas. The `attribute` variable can be found in line **233** in the form of a string. The `betas` variable can be found on line **234** in the form of a list of integers. Running this script will generate image transformations for each beta within `betas` .

<br>

`selector.py`

Allows the user to continuously generate images. `attribute` and `beta` variables are determined via terminal input. It is recommended to use this script when getting to know the API.

<br>

For both scripts, the user must enter their [Extempo](https://www.extempo.rocks/) login information. The user will be prompted to enter an input upon running the script. 

<br>

**A special thanks to the creators of [Extempo](https://www.extempo.rocks/): Dr. Stefan Uddenberg, Rachit Shah, and Dr. Daniel Albohn for allowing us to use their model**