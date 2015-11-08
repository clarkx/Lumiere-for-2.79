# Lumiere

## Interactive Lightning add-on for Blender 
(Preview : https://www.youtube.com/watch?v=ZF3Xf5lxZOk&list=PLG2jIUa3pBt5XRYJjSi6UA5PWUitH2Rud)
****
Control and positioned your light with the mouse directly on your model. Adjust the energy and scale interactively.

Use blender light, panel light, HDRI, background sky or draw your own light with the grease pencil. 

Add gradient texture to mimic professional light panel or use real HDRI.

### Create a new light :
> **Warning** : You have to apply the transform rotation and scale ("CTRL+A") for the moment, it's a todo.

Select the type of your light. Click on "Add Light". 

In the first 3dView, use "CTRL + Left Click" on your object to add your light. You are in interactive mode. To release the light use "Right Click" or "Escape". The light will be automatically parented to your object.

#### Target :
Allow you to control the light only with this object

#### Smooth :
Soften the light falloff

#### Light Falloff :
Use the **Quadratic**, **Linear** or **Constant** falloff

### Controls :
>By default :
> - the light will be place at 0,5 blender unit from your object
> - the angle of the light is compute by using the view3D

#### Interactive mode :

**"ALT + Mouse move"** : Range of the light from your model

**"Left Shift + Mouse move"** : Energy of the light

**"N"** : Alternate the angle from the view to the normal (try on a plane object to see the difference)

**"I"** : Alternate the light to the front to the back of the object ('Invert' the light angle)

**"F"** : Alternate the falloff types : *Quadratic*, *Linear*, *Constant*

#### Blender light : 
> (**"HEMI"** is not supported)

"Point", "Sun", "Spot", "Sky" : **"S"** to change the softness of the shadow 

"Area" : **"S"** to scale the light


#### Panel light :

**"Z"** : scale on the Y axis

**"S"** : scale the light on the XY axis

**"X"** : scale the light on the X axis

**"UP Arrow"** : Add a side to the shape

**"DOWN Arrow"** : Delete a side to the shape

#### Gradient :
> **Warning** : You have to select the index (the number on the the left of the list) before changing the value or the color.

**"+"** : Add a color stop to the coloramp

**"-"** : Delete a color stop to the coloramp

#### Gid shape :

**"Z"** : scale the row on the Y axis

**"SHIFT + Z"** : scale the gap between the rows on the Y axis

**"S"** : scale the light on the XY axis

**"X"** : scale the column on the X axis

**"SHIFT + X"** : scale the gap between the columns on the X axis

**"UP Arrow"** : Add a row to the grid

**"DOWN Arrow"** : Delete a row to the grid

**"RIGHT Arrow"** : Add a column to the grid

**"LEFT Arrow"** : Delete a column to the grid

TODO :
======
- ~~Add BGL~~ 
- ~~Finish the "Star shape"~~
- ~~Add a "Grid shape"~~
- Add undo
- Add an empty to the target object to control all the lights
- ~~Remove the apply transform (CTRL+A)~~
- ~~Add interpolation~~
- ~~Add list of lights~~
- ~~Add mute all lights but active one~~

