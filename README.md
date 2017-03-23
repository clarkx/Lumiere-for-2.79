# Lumiere

## Interactive Lighting add-on for Blender 
Wiki : https://github.com/clarkx/Lumiere/wiki

## Installation :
- Click on the script "Lumiere_beta.py",
- Click on the "RAW" button to see the script in your web browser,
- Right Click "Save as...", to save the script with the ".py" extension on your computer (ie: "Lumiere_beta.py")
- In the blender preferences, click on the "Add-ons" tab then on "Install from file..." to open the file browser,
- Select the file you just have save "Lumiere_beta.py" to finish the installation.
- A new tab "Lumiere" should appear.


Changelog :
Ver 0.8 :
- Update the doc in the [WIKI](https://github.com/clarkx/Lumiere/wiki#lumiere)
- Update panel light 
  - Add the "Keep ratio" option 
    - keep the amount of light when scaling
    - keep the shape in reflection with the range
- Update lights 
  - add an empty again for duplication and less memory usage
  - add a delete icon to easily remove everything fast
  - add a "change to" option to change this light to any another one
  - change the ui with all the options
  - Add "Repeat" option in the gradient
  - Add "Random" option in the gradient that can be used with grid color or texture
  
- Add the projector
  - project texture or diffuse the light as a softbox
- Add Environment lighting
  - Use your image environment interactively
  - "Align to pixel" option to align your light source with the interactive view
  - "Change to" option, to change the widget to a sun light

Ver 0.72 :
- All modal :
  - No need to press the key all the time. Exemple : Press [S] one time to scale the light, press [S] a second time or [LMB] to exit the modal mode.
  - Bugfix : Creating light during the edit mode was buggy / Use the image texture template.

****
Ver 0.71 :
- Update constraints :
  - An empty was created with each light for the contraints ("G" : Orbit mode), which was painful to delete. No more empty !

****
Ver 0.70 :
- Update UI :
  - Add a selection widget. The switch turns red to show you what light was selected.
  - Move the strengh in the upper of the panel. Easier to acces.
  - Bug fixes.

****
Ver 0.65 :
- New Reflector option : 
  - Turn your light into a diffuse object
 
****
Ver 0.60 :
- New custom light button:
  - Create you shape facing the z-axis and use the new "Create light" button
  - Example : https://www.youtube.com/watch?v=2c62-X2ugMs

****
Ver 0.55 :
- New gradient template by Nathan Craddock (thanks :+1: )
- Revert the mouse move to the left for decrease value, as request by VertexPainter
- Hotkeys mapping as request by VertexPainter
- Add HUD

****
