# 🦠 CellSePi – Cell Segmentation Pipeline 🦠

[![PyPI version](https://img.shields.io/pypi/v/cellsepi.svg)](https://pypi.org/project/cellsepi/)
[![License](https://img.shields.io/pypi/l/cellsepi.svg)](LICENSE)
[![PyPI Downloads](https://img.shields.io/pypi/dm/cellsepi.svg)](https://pypi.org/project/cellsepi/)
[![Last Commit](https://img.shields.io/github/last-commit/PraiseTheDarkFlo/cellsepi.svg)](https://github.com/PraiseTheDarkFlo/cellsepi)
![GitHub Repo stars](https://img.shields.io/github/stars/PraiseTheDarkFlo/cellsepi)
![GitHub forks](https://img.shields.io/github/forks/PraiseTheDarkFlo/cellsepi)
![GitHub issues](https://img.shields.io/github/issues/PraiseTheDarkFlo/cellsepi)

> **Data analysis software, which supports modular pipelining of analysis tasks including segmentation and fine-tuning of microscopy images, powered by Cellpose and spot detection using the Big-Fish library.**

## 🌟 Highlights

- **User-Friendly Interface:** Intuitive GUI for seamless image segmentation.
- **Modularization:** Personalize your data analyzis process by constructing an individual execution pipeline 
- **Advanced Segmentation:** Leverage different Cellpose models for accurate cellular segmentation.
- **Correction Tools:** Easily refine and correct segmentation results with an integrated drawing tool.
- **Custom Model Training:** Train and fine-tune models with your own data.
- **Batch Processing:** Process multiple images simultaneously.
- **Multi-Format Support:** Compatible with `.lif`, `.tif`/`.tiff`/`ome.tif`/`ome.tiff`, `.nd2`/`.nd2` and `.czi` image formats.
- **Fluorescence Readout:** Automatically extract fluorescence data.
- **Configurable Profiles:** Save and manage processing parameters effortlessly.
- **Adjustable Image Settings:** Manually or automatically fine-tune contrast and brightness.

## Table of Contents
* [Overview](#overview)
* [Usage](#-usage)
* [File Type Support](#file-type-support)
* [Model Support](#model-support)
* [Interface](#interface)
* [Functionalities](#functionalities)
* [Training](#training)
* [Modular Workflow Pipeline](#modular-workflow-pipeline)
* [Guides](https://github.com/CellSePi/CellSePi/blob/main/README.md#%EF%B8%8F-guides)
* [Build](#build)
* [Citations](https://github.com/CellSePi/CellSePi/blob/main/README.md#-citations)
* [Authors](#authors)
* [License](#license)
* [How To Cite](#how-to-cite)
* [Feedback & Contributions](#feedback--contributions)



## Overview

This project was developed in the context of a Bachelor project commissioned by the [Self-Organizing Systems Lab](https://www.bcs.tu-darmstadt.de/welcome/index.en.jsp) of the Technical University Darmstadt and supervised by [Erik Kubaczka](https://github.com/ERIK-KE) and Anja J. Engel. 

CellSePi is a powerful cell segmentation pipeline designed for microscopy images, featuring an interactive GUI to streamline your workflow. By utilizing the advanced Cellpose segmentation engine, CellSePi empowers researchers to efficiently process and analyze cellular images.

## 🚀 Usage

### Via the Executable
1. Navigate to the `Release` section on GitHub.
2. Choose the wanted release and select the necessary operating system version:`Linux`, `MacOS` or `Windows`
3. Download the executable
4. *If downloaded a split release:* Follow the *How-to-combine-archives*-guide in [Guides](#-guides)  

### Via the Terminal

Run the following command to launch the GUI:

```bash
  python -m cellsepi
```
### Further Information
> **Note:** MacOS blocks execution of release.  
> (Similar warning on Windows)  
> 
> *Do the following steps once:*  
> - Execute CellSePi (a MacOS window will pop up)
> - Close the window and CellSePi 
> - Open Settings 
> - Got to privacy and security 
> - Scroll down to security 
> - Click on execute CellSePi 
> - Follow instructions   

> **Note:**  Install Zently, when using the portable Linux archive (.tar.xz). Follow the instructions provided in [Guides](#-guides)

> **Note:**  You have to add the flet icon manually, if app downloaded as portable archive for linux.  
> 
> Run the included script:
> ```
> ./install_desktop_icon.sh
> ```

## File Type Support
`Lif`  
`ND2 / ND2 Dir`   
`CZI`  
`OME-TIFF / TIFF Dir`

Both 2D and 3D images are supported.   
3D images are viewed through Mean- or Max-Projection. 

## Model Support
The following Cellpose models are currently available for segmentation:    

`Sam / Sam v2`  
`DINO / Small DINO`  
`Cyto`  
`Nuclei`

> **Note:** You can also select a custom Cellpose model from your directory.

## Interface  
Main Window Start Screen

![Main Window Start Screen](docs/images/main_window_without_images.png?raw=true)

Main Window with Loaded Images

![Main Window with Images](docs/images/start_screen_with_image.png?raw=true)


## Functionalities 

**Menu**
- **Settings:** Configure cache, performance, image and segmentation options 
- **Dark/Light mode:** Adapts to your system settings. The changed theme is only active for the current session
- **Plugins:** Import new modules
- **Error log:** Information about errors during pipeline execution
- **Mask and outline colors:** Can be customized and are saved between sessions
- **Mask opacity:** Can be changed for the current session
- **CPU/GPU support:** Switch between CPU and GPU execution, if supported version was downloaded
> **Note:** For GPU support the specific GPU release needs to be downloaded, if using Linux or Windows. Within MacOS GPU acceleration is natively integrated.

![Menu](docs/gifs/Menu.gif?raw=true)

**Settings**   
Configure characteristics of the cache, application performance, segmentation and image adjustments through the provided setting interface:   

Cache:
- **Cutoff:** Amount of image and mask directories stored in cache

Performance: 
- **Segmantation downscaling:** Set mode, maximum pixels and maximum fraction applied during segmentation 
- **Visualization downscaling:** Set mode, maximum pixels and maximum fraction applied in the window visualization

Image:   
- **Normalize Gallery:** Normalization applied to the image gallery
- **Margin:** Margin used between rows
- **Upper/Lower Quantil:** Quantil used during normalization

Segmentation:  
- **Mask Deletion Diameter:** Deletes cells detected during segmentation below the specified diameter

There are already default settings provided at the first usage. Later changes can be saved or reseted to default.

![Settings](docs/gifs/Settings_GIF.gif?raw=true)

**Export**   
Export images and masks via the provided button.   
When exporting the data, it is possible to choose the storage directory.

![Export](docs/images/Export_mask_images_button.png?raw=true)


**Profiles**  
Save and manage the following parameters:

- **Bright-Field Channel:**  
  The channel on which segmentation is performed and whose masks are currently displayed.

- **Channel Prefix:**  
  The prefix in the image name that separates the series name and the channel. For example, if the channel prefix is set to `c`, the images `series100c1` and `series100c2` are recognized as part of series100 with channels 1 and 2.

- **Mask Suffix:**  
  Specifies the suffix that is used to identify and create the masks of the corresponding images. For instance, `series100c1_seg` is recognized as the mask for the image `series100c1`.

- **Diameter:**  
  Represents the average cell diameter used by the segmentation model.

> **Note:** Changes to the **Mask Suffix** or **Channel Prefix** will only take effect when new files are loaded.


![Profiles](docs/gifs/Profile_Gif.gif?raw=true)

**Segmentation**  
To start segmentation process select:
- A compatible model (see [Model Support](#model-support))
- A file with a valid filetype (see [File Type Support](#file-type-support))  


You will be alerted if you selected an incompatible model, when trying to start the segmentation. 

When starting the segmentation, choose the following: 
- **Overwrite:** Segment all images and delete preexisting masks 
- **Continue:** Segment only images with missing mask

During segmentation, you can:
- **Pause:** Temporarily halt the process and resume later.
- **Cancel:** Abort the process, reverting to the previous masks or removing them if none existed before.

![Segmentation](docs/gifs/Segmentation.gif?raw=true)


**Readout**  
Generates an `.xlsx`, `.tsv`, `.csv` or `.pdf` file containing the extracted fluorescence values. Click the "Open fluorescence file" button to launch your system’s default spreadsheet application with the generated file (e.g. ONLYOFFICE as seen below).

![Readout](docs/gifs/fluroscence_readout.gif?raw=true)

**Correction Tools**  
Correct segmentation errors manually or draw masks to train new models.  
- **Cell ID Shifting:** Automatically adjusts cell IDs to maintain a consecutive numbering when a cell is deleted.
- **Drawing:** Draw own cells. Finishes the outline and fills the cell with color automatically 
- **Deletion:** Delete an unwanted cell or all cells
- **Undo/Redo changes:** If the deletion or drawing is not to your liking, you are able to reverse the made changes


The Drawing Tools are fully integrated into the flet application (no separate application or window needed). Changes to the image will occur immediately. 

![Drawing Tools](docs/gifs/drawing_tools.gif?raw=true)

**Cell ID Overlay**   
Display the IDs and fluorescence values of the cells identified in the image to get a preview of the readout. The number next to the ID button indicates how many masks are present: 

![Mask_value](docs/images/Amount_of_masks_value.png?raw=true)
 
The visualization of the IDs can be invoked by hovering over the mask in the image.

![CellID](docs/gifs/cell_id_overlay.gif?raw=true)

**Brightness and Contrast**  
Enhance the visibility of your image by using the brightness and contrast sliders. The "Auto brightness and contrast" button automatically adjusts and normalizes the image.  

![Brightness Contrast](docs/gifs/brightness_contrast.gif?raw=true)

**Average Diameter**  
The average diameter of all cells over all images is displayed and updated with every change in the masks. The cell diameter is approximated by assuming circular cells and calculating the diameter from the area.  

![Average Diameter](https://github.com/PraiseTheDarkFlo/CellSePi/blob/main/docs/images/average_diameter.png?raw=true)

**Plugin System**    
Add new data analysis steps to enhance and personalize your workflow. 

Solely, upload an implemented python script through the Plugin function in the menu. No further steps required. 

![PluginSystem](docs/gifs/PluginSystem.gif?raw=true)

## Training  
Train your own models using the **Cellpose** framework. Two training modes are available:
1. **New Model Training:** Train a model from scratch using standard Cellpose models (`sam`, `sam v2`, `nuclei`, `cyto`, `cyto2` or `cyto3`).
2. **Model Fine-Tuning:** Retrain an existing model with your own images and masks for improved performance.

During training: 
- **Cancel:** Terminate the training
- **Logging:** See the training progress in the provided field

![Training](https://github.com/PraiseTheDarkFlo/CellSePi/blob/main/docs/gifs/training.gif?raw=true)

## Modular Workflow Pipeline
Create personalized execution pipelines to adapt the microscopy image analysis workflow according to individual needs.

**Modules**  
Encode functionality of the analysis task. Choose one or multiple to build the foundation of the pipeline. 

Functionalities: 
- **Add Connection:** Connect multiple modules
- **Option Settings:** Configure the functionality behind the module
- **View Ports:** See incoming and outcoming data 
- **Copy:** Use instead of dragging and dropping to add the module to the pipeline

For further information on how to create a new module, use the following link: https://cellsepi.github.io/CellSePi/

**Pipeline Menu**

- **Load Pipeline:** Import already constructed pipelines from the directory
- **Save as Pipeline/Save Pipeline:** Option to store the pipeline for later usage
- **Open Run Menu**: Start the pipeline execution and see the execution progress
- **Delete options:** Delete the pipeline connections 
- **Port overview:** Adds description to the edges in the pipeline 

![PipelineMenu](docs/images/PipelineMenu.png?raw=true)


**Pipeline Construction**  
- Drag and drop the available, required modules into the field 
- Connect the modules in the wished for order (If a connection is not possible or not all mandatory inputs are satisfied, the application will alert you).
- Configure the module settings


![PipelineConstruction](docs/gifs/PipelineConstruction.gif?raw=true)


**Pipeline Execution**  
To start execution:
- Select a valid pipeline
- Open the run tile in the pipeline menu and start the execution

During execution: 
- **Cancel:** Abort the process and restart it later.

In the run menu the progress of the execution pipeline and the amount of finished modules is indicated through the progress bar and ring.

> **Note:** During the execution it is not possible to exit the application. This would lead to the termination of the execution.

![PipelineExecution](docs/gifs/PipelineRun.gif?raw=true)

## ⬇️ Guides

### Zenty Installation Guide 
*(only necessary for installation via folder on linux)*

The application relies on Zenity to display graphical pop-up windows and dialog boxes (such as file pickers). Without it, certain features will fail to open, or the app may crash. 
 
If you installed the app via the system packages like .deb, .rpm, or Arch, you can safely ignore this step! Your package manager handles this dependency automatically.

Use the following command for the package manager, if Zenty is not pre-installed on the system:


  Ubuntu / Debian / Mint:
```bash  
  Bash
  sudo apt install zenity
```
  Arch Linux / Manjaro:
```bash  
  Bash
  sudo pacman -S zenity
```
  Fedora / RHEL:
```bash  
  Bash
  sudo dnf install zenity
```  
<br>

### How-to-combine-archives-Guide
Due to file size limits, some large releases may be split into multiple parts (e.g., ending in .partaa, .partab, etc.). If your downloaded release contains these files, you must combine them into a single archive before extracting.

- Place all parts in the same folder
- Open your terminal or command prompt in that folder
- Use the command for your operating system:

Linux / macOS:
```
cat cellsepi_*.part* > cellsepi_combined_archive.tar.xz
```
Windows (PowerShell):
```
cmd /c copy /b cellsepi_*.part* cellsepi_combined_archive.zip
```
## Build

```bash
  python -m cellsepi build
```
  For Windows, you need [Visual Studio 2022](https://learn.microsoft.com/en-us/visualstudio/install/install-visual-studio?view=vs-2022) with Desktop development with C++ workload installed ([Flet Windows build docs](https://flet.dev/docs/publish/windows/)).



## 📚 Citations

Our segmentation and models are powered by [CellPose](https://github.com/MouseLand/cellpose) 
and our spot detection is powered by [Big-FISH](https://github.com/fish-quant/big-fish).

- **Stringer, C., Wang, T., Michaelos, M., & Pachitariu, M. (2021). Cellpose:**  
  a generalist algorithm for cellular segmentation. *Nature Methods, 18*(1), 100-106.
- **Pachitariu, M. & Stringer, C. (2022). Cellpose 2.0:**  
  how to train your own model. *Nature Methods, 1-8.*
- **Stringer, C. & Pachitariu, M. (2025). Cellpose3:**  
  one-click image restoration for improved segmentation. *Nature Methods.*
- **Marius Pachitariu, Michael Rariden, and Carsen Stringer. Cellpose-sam:** superhuman
generalization for cellular segmentation.* bioRxiv, 2025.*
- **Eva Maxfield Brown, Dan Toloudis, Jamie Sherman, Madison Swain-Bowden, Talley Lambert, Sean Meharry, Brian Whitney, AICSImageIO Contributors (2023). BioIO:**  
  Image Reading, Metadata Conversion, and Image Writing for Microscopy Images in Pure Python [Computer software]. [GitHub](https://github.com/bioio-devs/bioio)
- **dilli_hangrae(2024):**
  Scanline Filling Algorithm. [Website](https://medium.com/@dillihangrae/scanline-filling-algorithm-852ad47fb0dd)
- **Arthur Imbert, Wei Ouyang, Adham Safieddine, Emeline Coleno, Christophe Zimmer, Edouard Bertrand, Thomas Walter, Florian Mueller. FISH-quant v2:** a scalable and modular analysis tool for smFISH image analysis. bioRxiv (2021) [Paper](https://doi.org/10.1101/2021.07.20.453024)

## ✍️ Authors

Developed by:  
- **Jenna Ahlvers** – [GitHub](https://github.com/Jnnnaa)  
- **Santosh Chhetri Thapa** – [GitHub](https://github.com/SantoshCT111)  
- **Nike Dratt** – [GitHub](https://github.com/SirHenry10)  
- **Pascal Heß** – [GitHub](https://github.com/Pasykaru)  
- **Florian Hock** – [GitHub](https://github.com/PraiseTheDarkFlo)

## 📝 License

This project is licensed under the **Apache License 2.0** – see the [LICENSE](LICENSE) file for details.

## 📖 How to cite 
If you use our repository in you own work, please cite us as follows: 
```
Jenna Ahlvers,Santosh Chhetri Thapa, Nike Dratt, Pascal Heß, Florian Hock(2025). CellSePi: Cell Segmentation Pipeline[computer software]. GitHub. https://github.com/PraiseTheDarkFlo/CellSePi
```
or as bibtext: 
```
@misc{cellsepi,
  author    = {Ahlvers, Jenna and Chhetri Thapa, Santosh and Dratt, Nike and Heß, Pascal and Hock, Florian},   
  title     = {CellSePi: Cell Segmentation Pipeline},  
  year      = {2025},  
  publisher = {GitHub},  
  url       = {https://github.com/PraiseTheDarkFlo/CellSePi}  
}
```

## 💭 Feedback & Contributions

Report bugs or suggest features via [GitHub Issues](https://github.com/PraiseTheDarkFlo/CellSePi/issues).
