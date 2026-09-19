# RIMO-PROJECT

Natural-language-controlled autonomous mobile robot, built on the LIMO platform. A spoken/typed command is turned into robot motion through an LLM-based intent pipeline, combined with vision-based perception and path planning for autonomous navigation.

## What it does

- **Natural language → robot control**: user commands are parsed by an LLM (Ollama / Llama 3.1) and translated into `cmd_vel` motion commands.
- **Object detection & interaction**: YOLO-based perception drives autonomous obstacle avoidance and a "greet" mode — the robot searches for a person, approaches, and greets them.
- **Autonomous navigation**: A* path planning combined with Pure Pursuit for map-based driving.
- **End-to-end pipeline**: React frontend → Django backend → SSH connection to the LIMO robot, so commands issued from the browser reach the physical robot.

## Tech stack

| Layer | Tech |
|---|---|
| Robot control | ROS2, LIMO SDK |
| Perception | YOLO (object detection) |
| Language → intent | Ollama, Llama 3.1 |
| Navigation | A*, Pure Pursuit |
| Backend | Django |
| Frontend | React |

## My contributions

This is a team project; my individual contributions include:

- ROS2 integration pipeline for LIMO robot control
- Direct SSH-based connection pipeline linking the frontend, Django backend, and the LIMO robot
- YOLO-based object tracking and natural-language mode routing (switching between navigation / detection / greet modes)
- YOLO-based "greet" mode: person search → approach → greet behavior
- Simplified the frontend to a single-screen English-language LIMO control UI

## Team

Built with [Joonsangpark1](https://github.com/Joonsangpark1) and other collaborators, evolved from an earlier intent-translation controller project.
