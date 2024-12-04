# Sight360
Sight360 is an AI-powered accessibility app designed to enhance the lives of visually impaired individuals by providing real-time environmental awareness, object detection, path navigation, and social interaction support. By integrating advanced technologies like AI, machine learning, and computer vision, Sight360 empowers users to navigate safely, recognize objects, understand their environment, and foster meaningful social connections.

## Overview
Visually impaired individuals often face challenges in perceiving and interacting with their surroundings. Sight360 aims to address these challenges by offering the following features:

- Environment Description: Real-time descriptions of the user's environment, including objects, people, and obstacles, allowing users to better understand and navigate their surroundings.
- Object Detection and Tracking: Identifies and tracks objects of interest in the environment, helping users locate and interact with them effectively.
- Path Navigation: Provides step-by-step instructions and audio cues for safe navigation, reducing the risk of accidents or getting lost, especially in unfamiliar environments.
- Face Detection and Facial Inference: Recognizes familiar faces and infers key attributes such as age, gender, and emotions, facilitating improved social connections and communication.

## Features
- Environment Awareness: Using the BLIP model, the app describes the user’s environment, detecting objects, people, and obstacles.
- Object Detection & Tracking: YOLOv5 is used to recognize and track objects, enabling users to interact with the environment.
- Depth Estimation: MIDAS is used to calculate the distance of objects from the user to enhance navigation.
- Facial Recognition: With DeepFace, the app recognizes familiar faces and infers key attributes (emotion, age, gender).
- Path Navigation: Audio cues guide the user through safe paths, including step-by-step instructions (e.g., forward, left, right, stop).

## Tech Stack
- OpenCV: For real-time computer vision processing.
- Deep Learning: Machine learning models for object detection, face recognition, and environment description.
- YOLOv5: For object detection.
- MIDAS: For depth estimation.
- DeepFace: For facial recognition and analysis.
- BLIP: For environment description.
- ElevenLabs: For AI-powered speech synthesis.
- PyQt: For the GUI.

