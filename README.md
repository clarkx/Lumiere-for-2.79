# Lumiere

## Interactive Lightning add-on for Blender 
(Preview : https://www.youtube.com/watch?v=ZF3Xf5lxZOk&list=PLG2jIUa3pBt5XRYJjSi6UA5PWUitH2Rud)
****
Control and positioned your light with the mouse directly on your model. Adjust the energy and scale interactively.

Use blender lamp, panel light, HDRI, background sky. 

Add gradient texture to mimic professional light panel, soft box or use real HDRI.

### Create a new light :
Select the type of your light. Click on "Add Light". 

In the first 3dView, use "CTRL + Left Click" on your object to add your light. You are in interactive mode. To release the light use "Right Click" or "Escape". The light will be automatically parented to your object.

#### Interactive mode : ![interactive_mode](https://cloud.githubusercontent.com/assets/10100090/12847889/c100eac0-cc16-11e5-8b45-62334a23d06f.png)

**"Left mouse button"** : Align the light with the refection or the normal of the target object (see **"N"** option).
![interactive mode](https://cloud.githubusercontent.com/assets/10100090/12848961/2846ade0-cc1d-11e5-9f37-ee2158d678ae.gif)

**"ALT + Mouse move"** : Range of the light from your model

**"Left Shift + Mouse move"** : Energy of the light

**"N"** : Alternate the angle from the view to the normal (try on a plane object to see the difference)

**"F"** : Alternate the falloff types : *Quadratic*, *Linear*, *Constant*

**"G"** : Grab the light and orbit around the target point :
![grab](https://cloud.githubusercontent.com/assets/10100090/12847098/44bc2d3a-cc11-11e5-90bc-1ebc247e200c.gif)

#### Ghost mode : ![hid_all_but_this_one](https://cloud.githubusercontent.com/assets/10100090/12847858/8a4e8230-cc16-11e5-9ae5-dcff99322653.png)
Hide all the light save this one.
![hid_all_but_the_light](https://cloud.githubusercontent.com/assets/10100090/12847114/5cfc1b4e-cc11-11e5-8a91-963edd456cd8.gif)

#### Hide light :![not_hid_lamp](https://cloud.githubusercontent.com/assets/10100090/12848322/6eac6332-cc19-11e5-825f-ffd3aa9d7f91.png) // ![hid_lamp](https://cloud.githubusercontent.com/assets/10100090/12848324/7086b270-cc19-11e5-8659-a52ad24deb26.png)
Hide/Unhide the selected lamp
![hid_light](https://cloud.githubusercontent.com/assets/10100090/12847118/6085d304-cc11-11e5-8006-fd375703e53f.gif)

#### Target :
Allow you to control the light only with this object
![target](https://cloud.githubusercontent.com/assets/10100090/12847216/f8b8708c-cc11-11e5-9eef-ffd09ea77705.gif)

#### Light settings :
**MIS** : Multiple Importance Sampling - Reduce noise

**Shadows** : Only for lamp - cast shadows or not

**Diff** : Diffuse reflection rays

**Spec** : Specular reflection rays

![surface_settings](https://cloud.githubusercontent.com/assets/10100090/12847186/c49a66de-cc11-11e5-91cf-935706d09447.gif)

#### Light Falloff :
Use the **Quadratic**, **Linear** or **Constant** falloff
![falloff](https://cloud.githubusercontent.com/assets/10100090/12847374/244c7850-cc13-11e5-80d7-6cb41a01c6cb.gif)

#### Smooth :
Soften the light falloff 
![smooth_falloff](https://cloud.githubusercontent.com/assets/10100090/12847369/1987651a-cc13-11e5-851f-df5671225fcc.gif)

### Controls :
>By default :
> - the light will be place at 0,5 blender unit from your object
> - the angle of the light is compute by using the view3D

#### Blender lamps : 
> (**"HEMI"** is not supported)

"Point", "Sun": **"S"** to change the softness of the shadow 

"Spot" : **"S"** to change the softness of the shadow // **"Z"** : Change the spot blend // **"X"** : Change the spot size
![spot_lamp](https://cloud.githubusercontent.com/assets/10100090/12847150/8661f8e6-cc11-11e5-958c-c747f5d324f5.gif)

"Area" : **"S"** to scale the light on the XY axis // **"X"** : scale the light on the X axis // **"Z"** : scale on the Y axis
![area_lamp](https://cloud.githubusercontent.com/assets/10100090/12847078/2cadd996-cc11-11e5-80ae-f95a36ada200.gif)

"Sky" : **"S"** to change the softness of the shadow // The view angle will automatically change the light color
![sky](https://cloud.githubusercontent.com/assets/10100090/12847125/641cd83c-cc11-11e5-812f-d49277f14798.gif)

#### Panel light :

**"Z"** : scale on the Y axis

**"S"** : scale the light on the XY axis

**"X"** : scale the light on the X axis

**"Page UP"** : Add a side to the shape
![add_shape](https://cloud.githubusercontent.com/assets/10100090/12847072/2737a776-cc11-11e5-96d8-88ce0a79b26a.gif)

**"Page DOWN"** : Delete a side to the shape
![less_shape](https://cloud.githubusercontent.com/assets/10100090/12847121/62a2165c-cc11-11e5-981b-cc73516eb048.gif)

#### Gradient :

**"+"** : Add a color stop to the coloramp

**"-"** : Delete a color stop to the coloramp

Gradient Types: 
![gradient_types](https://cloud.githubusercontent.com/assets/10100090/12847101/48792b12-cc11-11e5-9a0d-07988464fead.gif)

Interpolation : Change the blending of the colors
![gradient_interpolation](https://cloud.githubusercontent.com/assets/10100090/12847100/46aabd8c-cc11-11e5-8fb7-e5e69574c3e5.gif)

#### Texture :
Add a diffuse color texture to your light (only panel light)
![hdri_texture](https://cloud.githubusercontent.com/assets/10100090/12847112/598f4da0-cc11-11e5-851d-d34c13d54da7.gif)

#### Gid shape :

**"Z"** : scale the row on the Y axis

**"S"** : scale the light on the XY axis

**"X"** : scale the column on the X axis

**"SHIFT + Z"** : scale the gap between the rows on the Y axis // **"SHIFT + X"** : scale the gap between the columns on the X axis

**"UP Arrow"** : Add a row to the grid // **"DOWN Arrow"** : Delete a row to the grid

**"RIGHT Arrow"** : Add a column to the grid // **"LEFT Arrow"** : Delete a column to the grid
![grid](https://cloud.githubusercontent.com/assets/10100090/12847103/4c457ae8-cc11-11e5-8b02-e4e514f9a57f.gif)
