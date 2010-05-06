#   This file is part of VISVIS.
#    
#   VISVIS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Lesser General Public License as 
#   published by the Free Software Foundation, either version 3 of 
#   the License, or (at your option) any later version.
# 
#   VISVIS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Lesser General Public License for more details.
# 
#   You should have received a copy of the GNU Lesser General Public 
#   License along with this program.  If not, see 
#   <http://www.gnu.org/licenses/>.
#
#   Copyright (C) 2009 Almar Klein

""" Module polygonalModeling

This module defined the Mesh object that represents a polygonal model.
It also defines lights and algorithmic for managing polygonal models.

"""

from points import Point, Pointset
from misc import Property, getColor
from base import Wobject
from textures import TextureObjectToVisualize, Colormap

import numpy as np
import OpenGL.GL as gl


def _testColor(value, canBeScalar=True):
    """ _testColor(value)
    Tests a color whether it is a sequence of 3 or 4 values.
    It returns a 4 element tuple or raises an error if the suplied
    data is incorrect.
    """
    
    # Deal with named colors
    if isinstance(value, basestring):
        value = getColor(value)
    
    # Value can be a scalar
    if canBeScalar and isinstance(value, (int, float)):
        if value <= 0:
            value = 0.0
        if value >= 1:
            value = 1.0
        return value
    
    # Otherwise it must be a sequence of 3 or 4 elements
    elif not hasattr(value, '__len__'):
        raise ValueError("Given value can not represent a color.")
    elif len(value) == 4:
        return (value[0], value[1], value[2], value[3])
    elif len(value) == 3:
        return (value[0], value[1], value[2], 1.0)
    else:
        raise ValueError("Given value can not represent a color.")


def _getColor(color, ref):
        """ _getColor(color, reference)
        Get the real color as a 4 element tuple, using the reference
        color if the given color is a scalar.
        """
        if isinstance(color, float):
            return (color*ref[0], color*ref[1], color*ref[2], ref[3])
        else:
            return color


# todo: implement spot light and attenuation
class Light(object):
    def __init__(self, index):
        
        # Store index of the light (OpenGl can handle up to 8 lights)
        self._index = index
        self._on = False
        
        # The three light properties
        self._color = (1, 1, 1, 1)
        self._ambient = 0.0
        self._diffuse = 1.0
        self._specular = 1.0
        
        # The main light has an ambien component by default
        if index == 0:
            self._ambient = 0.2
        
        # Position or direction
        if index == 0:
            self._position = (0,0,1,0)
            self._camLight = True
        else:
            self._position = (0,0,0,1)
            self._camLight = False
    
    
    @Property
    def color():
        """ Get/Set the reference color of the light. If the ambient,
        diffuse or specular properties specify a scalar, that scalar
        represents the fraction of *this* color. 
        """
        def fget(self):
            return self._color
        def fset(self, value):
            self._color = _testColor(value, True)
    
    
    @Property
    def ambient():
        """ Get/Set the ambient color of the light. This is the color
        that is everywhere, coming from all directions, independent of 
        the light position. 
        
        The value can be a 3- or 4-element tuple, a character in 
        "rgbycmkw", or a scalar between 0 and 1 that indicates the 
        fraction of the reference color.
        """
        def fget(self):
            return self._ambient
        def fset(self, value):
            self._ambient = _testColor(value)
    
    
    @Property
    def diffuse():
        """ Get/Set the diffuse color of the light. This component is the
        light that comes from one direction, so it's brighter if it comes
        squarely down on a surface than if it barely glances off the 
        surface. It depends on the light position how a material is lit.
        
        """
        def fget(self):
            return self._diffuse
        def fset(self, value):
            self._diffuse = _testColor(value)
    
    
    @Property
    def specular():
        """ Get/Set the specular color of the light. This component
        represents the light that comes from the light source and bounces
        off a surface in a particular direction. This is what makes 
        materials appear shiny.
        
        The value can be a 3- or 4-element tuple, a character in 
        "rgbycmkw", or a scalar between 0 and 1 that indicates the 
        fraction of the reference color.
        """
        def fget(self):
            return self._specular
        def fset(self, value):
            self._specular = _testColor(value)
    
    
    @Property
    def position():
        """ Get/Set the position of the light. Can be represented as a
        3 or 4 element tuple. If the fourth element is a 1, the light
        has a position, if it is a 0, it represents a direction (i.o.w. the
        light is a directional light, like the sun).
        """
        def fget(self):
            return self._position
        def fset(self, value):
            if len(value) == 3:
                self._position = value[0], value[1], value[2], 1
            elif len(value) == 4:
                self._position = value[0], value[1], value[2], value[3]
            else:
                tmp = "Light position should be a 3 or 4 element sequence."
                raise ValueError(tmp)
    
    
    @Property
    def isDirectional():
        """ Get/Set whether the light is a directional light. A directional
        light has no real position (it can be thought of as infinitely far
        away), but shines in a particular direction. The sun is a good
        example of a directional light.
        """
        def fget(self):
            return self._position[3] == 0
        def fset(self, value):
            # Get fourth element
            if value:
                fourth = 0
            else:
                fourth = 1
            # Set position
            tmp = self._position 
            self._position = tmp[0], tmp[1], tmp[2], fourth
    
    
    @Property
    def isCamLight():
        """ Get/Set whether the light is a camera light. A camera light
        moves along with the camera, like the lamp on a miner's hat.
        """
        def fget(self):
            return self._camLight
        def fset(self, value):
            self._camLight = bool(value)
    
    
    def On(self, on=True):
        """ On(on=True)
        Turn the light on.
        """
        self._on = bool(on)
    
    
    def Off(self):
        """ Off()
        Turn the light off.
        """
        self._on = False
    
    
    @property
    def isOn(self):
        return self._on
    
    
    def _Apply(self):
        """ _Apply()
        Apply the light position and other properties.
        """
        thisLight = gl.GL_LIGHT0 + self._index
        if self._on:
            # Enable and set position            
            gl.glEnable(thisLight)
            gl.glLightfv(thisLight, gl.GL_POSITION, self._position)
            # Set colors
            amb, dif, spe = gl.GL_AMBIENT, gl.GL_DIFFUSE, gl.GL_SPECULAR
            gl.glLightfv(thisLight, amb, _getColor(self._ambient, self._color))
            gl.glLightfv(thisLight, dif, _getColor(self._diffuse, self._color))
            gl.glLightfv(thisLight, spe, _getColor(self._specular, self._color))
        else:
            gl.glDisable(thisLight)



def check3dArray(value):
    """ Check the shape of vertex/color/texcord data. 
    Always returns a numpy array. 
    """
    if isinstance(value, np.ndarray):
        if not (value.ndim == 2 and value.shape[1] == 3):
            raise ValueError()
        if value.dtype == np.float32:
            return value
        else:
            return value.astype(np.float32)
    elif isinstance(value, Pointset):
        if not value.ndim==3:
            raise ValueError()
        return value.data
    else:
        raise ValueError()


class Mesh(Wobject):
    """ Mesh(parent, vertices, normals=None, faces=None, 
        colors=None, texcords=None, verticesPerFace=3)
    
    A mesh is a generic object to visualize a 3D object made up of 
    polygons. These polygons can be triangles or quads. The mesh
    is affected by lighting and its material properties can be 
    changes using properties. Per vertex color can be supplied
    explicitly by giving a color array, by supplying 1D texcords which
    are looked up in the colormap, or by supplying a 2D texcords array
    and setting a 2D texture image.
    
    Vertices is a Nx3 numpy array of vertex positions in 3D space.
    
    Normals is a Nx3 numpy array of vertex normals. If not given, 
    it is calcululated from the vertices.
    
    Faces (optional) is a numpy array or list of indices to define the faces.
    If this array is Nx3 or Nx4, the type is inferred from this array. Faces
    should be of uint8, uint16 or uint32 (if it is not, the data is converted
    to uint32).
    
    Colors is a Nx3 numpy array giving the ambient and diffuse color for
    each vertex. 
    
    Texcords is used to map a 2D texture or 1D texture (a colormap) to the
    mesh. The texture color is multiplied after the ambient and diffuse
    lighting calculations, but before calculating the specular component.
    If texcords is a 1D (size N) array specifying the color index at each
    vertex. The texture-color at each vertex is then calculated by looking
    it up in the colormap. If texcords is a Nx2 array it represents the 2D
    texture coordinates to map an image to the mesh. Use SetTexture() to set 
    the image, and the colormap property to set the colormap.
    
    VerticesPerFace can be 3 or 4. It determines whether the faces are
    triangles or quads. If faces is specified and is 2D, the number of
    vertices per face is determined from that array.
    """ 
    
    def __init__(self, parent, vertices, normals=None, faces=None, 
            colors=None, texcords=None, verticesPerFace=3):
        Wobject.__init__(self, parent)
        
        # Set type first (can be reset by faces)
        verticesPerFace = int(verticesPerFace)
        if verticesPerFace in [3, 4]:
            self._verticesPerFace = verticesPerFace
        else:        
            raise ValueError('VerticesPerFace should be 3 or 4.')
        
        # Set all things (checks are performed in set methods)
        self.SetVertices(vertices)
        self.SetNormals(normals)
        self.SetFaces(faces)
        self.SetColors(colors)
        self.SetTexcords(texcords)
        
        # Init flat normals
        self._flatNormals = None
        
        # Create colormap and init texture
        self._colormap = Colormap()
        self._texture = None
        
        # What faces to cull
        self._cullFaces = None #gl.GL_BACK
        
        # Material properties
        self._color = (1, 1, 1, 1)
        self._ambient = 0.7
        self._diffuse = 0.7
        self._specular = 0.3
        self._shininess = 50
        self._emission = 0.0
    
    
    @Property
    def color():
        """ Get/Set the reference color of the object. If the ambient,
        diffuse or emissive properties specify a scalar, that scalar
        represents the fraction of *this* color. (If the specular
        property is a scalar, it represents a fraction of (1,1,1).)
        """
        def fget(self):
            return self._color
        def fset(self, value):
            self._color = _testColor(value, True)
    
    
    @Property
    def ambient():
        """ Get/Set the ambient reflection color of the material. Ambient
        light is the light that is everywhere, coming from all directions, 
        independent of the light position. 
        
        The value can be a 3- or 4-element tuple, a character in 
        "rgbycmkw", or a scalar between 0 and 1 that indicates the 
        fraction of the reference color.
        """
        def fget(self):
            return self._ambient
        def fset(self, value):
            self._ambient = _testColor(value)
    
    
    @Property
    def diffuse():
        """ Get/Set the diffuse reflection color of the material. Diffuse
        light comes from one direction, so it's brighter if it comes
        squarely down on a surface than if it barely glances off the 
        surface. It depends on the light position how a material is lit.
        
        The value can be a 3- or 4-element tuple, a character in 
        "rgbycmkw", or a scalar between 0 and 1 that indicates the 
        fraction of the reference color.
        """
        def fget(self):
            return self._diffuse
        def fset(self, value):
            self._diffuse = _testColor(value)
    
    
    @Property
    def ambientAndDiffuse():
        """ Set the diffuse and ambient component simultaneously. Usually,
        you want to give them the same value. Getting returns the diffuse
        component.
        """
        def fget(self):
            return self._diffuse
        def fset(self, value):
            self._diffuse = self._ambient = _testColor(value)
    
    
    @Property
    def specular():
        """ Get/Set the specular reflection color of the material. Specular
        light represents the light that comes from the light source and bounces
        off a surface in a particular direction. It is what makes 
        materials appear shiny.
        
        The value can be a 3- or 4-element tuple, a character in 
        "rgbycmkw", or a scalar between 0 and 1 that indicates the 
        fraction of white (1,1,1).
        """
        def fget(self):
            return self._specular
        def fset(self, value):
            self._specular = _testColor(value)
    
    
    @Property
    def shininess():
        """ Get/Set the shininess value of the material as a number between
        0 and 128. The higher the value, the brighter and more focussed the
        specular spot, thus the shinier the material appears to be.
        """
        def fget(self):
            return self._shininess
        def fset(self, value):
            if value < 0: value = 0
            if value > 128: value = 128
            self._shininess = value
    
    
    @Property
    def emission():
        """ Get/Set the emission color of the material. It is the 
        "self-lighting" property of the material, and usually only makes
        sense for objects that represent lamps or candles etc.
        
        The value can be a 3- or 4-element tuple, a character in 
        "rgbycmkw", or a scalar between 0 and 1 that indicates the 
        fraction of the reference color.
        """
        def fget(self):
            return self._emission
        def fset(self, value):
            self._emission = _testColor(value)
    
    
    @Property
    def cullFaces():
        """ Get/Set the culling of faces. Values can be 'front', 'back'
        or None (default). If 'back': backfacing faces are not drawn.
        """
        def fget(self):
            D = {gl.GL_FRONT:'front', gl.GL_BACK:'back', None:None}
            return D[self._cullFaces]
        def fset(self, value):
            if isinstance(value, basestring):
                try:
                    D = {'front':gl.GL_FRONT, 'back':gl.GL_BACK}
                    self._cullFaces = D[value.lower()]
                except KeyError:
                    raise ValueError('Invalid value for cullFaces')
            elif not value:
                self._cullFaces = None
            else:
                raise ValueError('Invalid value for cullFaces')
    
    
    ## Setters
    
    
    def SetVertices(self, vertices):
        """ SetVertices(vertices)
        Set the vertex data as a Nx3 numpy array or as a 3D Pointset. 
        """
        try:
            self._vertices = check3dArray(vertices)
        except ValueError:
            raise ValueError("Vertices should represent an array of 3D vertices.")
    
    
    def SetNormals(self, normals):
        """ SetNormals(normals)
        Set the normal data as a Nx3 numpy array or as a 3D Pointset. 
        """
        if normals is not None:
            try:
                self._normals = check3dArray(normals)
            except ValueError:
                raise ValueError("Normals should represent an array of 3D vertices.")
        else:
            self._normals = None
    
    
    def SetColors(self, colors):
        """ SetColors(colors)
        Set the color data as a Nx3 numpy array or as a 3D Pointset. 
        """
        if colors is not None:
            try:
                self._colors = check3dArray(colors)
            except ValueError:
                raise ValueError("Colors should represent an array of 3D vertices.")
        else:
            self._colors = None
    
    
    def SetTexcords(self, texcords):
        """ SetTexcords(texcords)
        Set the texture coordinates as a Nx2 numpy array or as a 2D Pointset.
        It can also be None to turn off the texture.
        """
        if texcords is not None:
        
            if isinstance(texcords, np.ndarray):
                # Test dimensions
                if texcords.ndim == 2 and texcords.shape[1] == 2:
                    pass # Texture coordinates
                elif texcords.ndim == 1:
                    pass # Colormap entries
                else:
                    raise ValueError("Texture coordinates must be 2D or 1D.")
                # Test data type
                if texcords.dtype == np.float32:
                    self._texcords = texcords
                else:
                    self._texcords = texcords.astype(np.float32)
            
            elif isinstance(texcords, Pointset):
                if not texcords.ndim==2:
                    raise ValueError("Texture coordinates must be 2D or 1D.")
                self._texcords = texcords.data
            else:
                raise ValueError("Texture coordinates must be a numpy array or Pointset.")
        
        else:
            self._texcords = None
    
    
    def SetFaces(self, faces):
        """ SetFaces(faces)
        Set the faces data. This can be either a list, a 1D numpy array,
        a Nx3 numpy array, or a Nx4 numpy array. In the latter two cases
        the type is set to GL_TRIANGLES or GL_QUADS respectively.
        """
        
        # Check and store faces
        if faces is not None:
            if isinstance(faces, list):
                self._faces = np.array(faces, dtype=np.uint32)
            elif isinstance(faces, np.ndarray):
                # Check shape
                if faces.ndim==1:
                    pass # ok
                elif faces.ndim==2 and faces.shape[1] in [3,4]:
                    self._verticesPerFace = faces.shape[1]
                else:
                    tmp = 'Faces should represent a list or, 1D, Nx3 or Nx4'
                    raise ValueError(tmp + ' numpy array.')
                # Check data type
                if faces.dtype in [np.uint8, np.uint16, np.uint32]:
                    self._faces = faces.reshape((faces.size,))
                else:                    
                    self._faces = faces.astype(np.uint32)
                    self._faces.shape = (faces.size,)
            else:
                raise ValueError("Faces should be a list or numpy array.")
            # Check
            if self._faces.min() < 0:
                raise ValueError("Face data should be non-negative integers.")
            if self._vertices is not None:
                if self._faces.max() >= len(self._vertices):
                    raise ValueError("Face data references non-existing vertices.")
        else:
            self._faces = None
    
    
    def SetTexture(self, data):
        if data is not None:
            # Check dimensions
            if data.ndim==2:
                pass # ok: gray image
            elif data.ndim==3 and data.shape[2]==3:
                pass # ok: color image
            else:
                raise ValueError('Only 2D images can be mapped to a mesh.')
            # Make texture object and bind
            self._texture = TextureObjectToVisualize(2, data)
            self._texture.SetData(data)
        else:
            self._texture = None
    
    @Property
    def colormap():
        """ Get/Set the colormap. The argument must be a tuple/list of 
        iterables with each element having 3 or 4 values. The argument may
        also be a Nx3 or Nx4 numpy array. In all cases the data is resampled
        to create a 256x4 array.
        
        Visvis defines a number of standard colormaps in the global visvis
        namespace: CM_AUTUMN, CM_BONE, CM_COOL, CM_COPPER, CM_GRAY, CM_HOT, 
        CM_HSV, CM_JET, CM_PINK, CM_SPRING, CM_SUMMER, CM_WINTER. 
        A dict of name-colormap pairs is also available as vv.cm.colormaps.
        """
        def fget(self):
            return self._colormap.GetMap()
        def fset(self, value):
            self._colormap.SetMap(value)
    
    
    ## Method implementations to function as a proper wobject
    
    def _GetLimits(self):
        """ _GetLimits()
        Get the limits in world coordinates between which the object exists.
        """
        
        vertices = self._vertices
        
        # Obtain untransformed coords         
        x1, x2 = vertices[:,0].min(), vertices[:,0].max()
        y1, y2 = vertices[:,1].min(), vertices[:,1].max()
        z1, z2 = vertices[:,2].min(), vertices[:,2].max()
        
        # There we are
        return Wobject._GetLimits(self, x1, x2, y1, y2, z1, z2)
    
    
    def OnDestroyGl(self):
        # Clean up OpenGl resources.
        self._colormap.DestroyGl()
        if self._texture is not None:
            self._texture.DestroyGl()
    
    
    def OnDestroy(self):
        # Clean up any resources.
        self._colormap.Destroy()
        if self._texture is not None:
            self._texture.Destroy()
    
    
    def OnDraw(self):
#         gl.glEnable(gl.GL_POLYGON_OFFSET_LINE)
#         gl.glPolygonOffset(-2.0,-2.0)
        self._DrawFaces()
#         self._DrawLines()
#         gl.glDisable(gl.GL_POLYGON_OFFSET_LINE)
    
    def _DrawFaces(self):
        
        # We need vertices
        if self._vertices is None:
            return
        
        # We need normals
        if self._normals is None:
            self.CalculateNormals()
        if self._flatNormals is None:
            self._CalculateFlatNormals()
        
        # Prepare for drawing
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glVertexPointerf(self._vertices)
        #
        gl.glEnableClientState(gl.GL_NORMAL_ARRAY)
        gl.glNormalPointerf(self._flatNormals)
        #
        if self._colors is not None:
            gl.glEnable(gl.GL_COLOR_MATERIAL)
            gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
            gl.glEnableClientState(gl.GL_COLOR_ARRAY)
            gl.glColorPointerf(self._colors)
        #
        if self._texcords is not None:
            if (self._texcords.ndim == 2) and (self._texture is not None):
                gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
                gl.glTexCoordPointerf(self._texcords)
                self._texture.Enable(0)
            elif self._texcords.ndim == 1:
                gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
                gl.glTexCoordPointer(1, gl.GL_FLOAT, 0, self._texcords)
                self._colormap.Enable(0)
        
        # Prepare material (ambient and diffuse may be overriden by colors)
        what = gl.GL_FRONT_AND_BACK
        gc = _getColor
        gl.glMaterial(what, gl.GL_AMBIENT, gc(self._ambient, self._color) )
        gl.glMaterial(what, gl.GL_DIFFUSE, gc(self._diffuse, self._color) )
        gl.glMaterial(what, gl.GL_SPECULAR, gc(self._specular, (1,1,1,1)) )
        gl.glMaterial(what, gl.GL_SHININESS, self._shininess)
        gl.glMaterial(what, gl.GL_EMISSION, gc(self._emission, self._color))
        
        # Prepare lights
        gl.glEnable(gl.GL_LIGHTING)
        #gl.glShadeModel(gl.GL_SMOOTH)
        gl.glShadeModel(gl.GL_FLAT)
        gl.glEnable(gl.GL_NORMALIZE)  # GL_NORMALIZE or GL_RESCALE_NORMAL
        
        # Set culling (take data aspect into account!)
        axes = self.GetAxes()
        tmp = 1
        if axes:
            for i in axes.daspect:
                if i<0:
                    tmp *= -1
        gl.glFrontFace({1:gl.GL_CW, -1:gl.GL_CCW}[tmp])
        if self._cullFaces:
            gl.glEnable(gl.GL_CULL_FACE)
            gl.glCullFace(self._cullFaces)
        
        # Draw
        type = {3:gl.GL_TRIANGLES, 4:gl.GL_QUADS}[self._verticesPerFace]
        if self._faces is None:
            gl.glDrawArrays(type, 0, self._vertices.shape[0])
        else:
            # Get data type
            if self._faces.dtype == np.uint8:
                face_dtype = gl.GL_UNSIGNED_BYTE
            elif self._faces.dtype == np.uint16:
                face_dtype = gl.GL_UNSIGNED_SHORT
            else:
                face_dtype = gl.GL_UNSIGNED_INT
            # Go
            N = self._faces.size
            gl.glDrawElements(type, N, face_dtype, self._faces)
        
        # Clean up
        gl.glFlush()
        if self._texcords is not None:
            self._colormap.Disable()
            if self._texture:
                self._texture.Disable()
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glDisableClientState(gl.GL_NORMAL_ARRAY)
        gl.glDisableClientState(gl.GL_COLOR_ARRAY)
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        gl.glDisable(gl.GL_COLOR_MATERIAL)
        gl.glPolygonMode(gl.GL_FRONT, gl.GL_FILL)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_CULL_FACE)
    
    
    def _DrawLines(self):
        
        # We need vertices
        if self._vertices is None:
            return
        
        # Prepare for drawing
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glVertexPointerf(self._vertices)
        
        # Draw lines
        gl.glColor(0,1,0,1) # todo: set color
        gl.glPolygonMode(gl.GL_FRONT, gl.GL_LINE)
        
        # culling
        gl.glFrontFace(gl.GL_CW)
        
        # Draw
        type = {3:gl.GL_TRIANGLES, 4:gl.GL_QUADS}[self._verticesPerFace]
        if self._faces is None:
            gl.glDrawArrays(type, 0, self._vertices.shape[0])
        else:
            # Get data type
            if self._faces.dtype == np.uint8:
                face_dtype = gl.GL_UNSIGNED_BYTE
            elif self._faces.dtype == np.uint16:
                face_dtype = gl.GL_UNSIGNED_SHORT
            else:
                face_dtype = gl.GL_UNSIGNED_INT
            # Go            
            faces = self._faces[:-3000]
            N = faces.size
            gl.glDrawElements(type, N, face_dtype, faces)
            #gl.glDrawElementsui(type, self._faces)
        
        # Clean up
        gl.glFlush()
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glPolygonMode(gl.GL_FRONT, gl.GL_FILL)
    
    
    # todo: implement shape
    def OnDrawShape(self, color):        
        pass
    
    
    ## Mesh processing
    
    
    def _WithoutFaces(self):
        """ _WithoutFaces()
        Unwinds the faces to make new versions of the vertices, normals,
        color and texCords, which are usually larger. The new arrays 
        represent the same surface, but is described without a faces
        array.
        """
        
        # Make new vertices and normals if faces are used
        if self._faces is not None:
            
            # Get references and new size
            faces = self._faces
            N = faces.shape[0]
            
            # Unwind vertices
            if self._vertices is not None:
                # Get ref and allocate new array
                vertices = self._vertices
                newVertices = np.zeros((N,3), dtype='float32')
                # Unwind
                for i in range(N):
                    newVertices[i,:] = vertices[faces[i]]
                # Store
                self._vertices = newVertices
            
            # Unwind normals
            if self._normals is not None:
                # Get ref and allocate new array
                normals = self._normals
                newNormals = np.zeros((N,3), dtype='float32')
                for i in range(N):
                    newNormals[i,:] = normals[faces[i]]
                # Store
                self._normals = newNormals
                self._flatNormals = None
            
            # Unwind color
            if self._colors is not None:
                # Get ref and allocate new array
                color = self._color
                newColor = np.zeros((N,3), dtype='float32')
                for i in range(N):
                    newColor[i,:] = color[faces[i]]
                # Store
                self._color = newColor
            
            # Unwind texcords
            if self._colors is not None:
                # Get ref and allocate new array
                texcords = self._texcords
                newTexcords = np.zeros((N,3), dtype='float32')
                for i in range(N):
                    newTexcords[i,:] = texcords[faces[i]]
                # Store
                self._texcords = newTexcords
            
            # Remove reference to faces
            self._faces = None
    
    
    def _IterFaces(self):
        """ _IterFaces()
        Iterate over the faces of the mesh. Each iteration
        yields a tuple of indices in the array of vertices. 
        The tuples had verticesPerFace elements.
        """
        
        if self._faces is None:
            
            if self._verticesPerFace == 3:
                for i in range(0, self._vertices.shape[0], 3):
                    yield i, i+1, i+2
            else:
                for i in range(0, self._vertices.shape[0], 4):
                    yield i, i+1, i+2, i+3
        
        else:
            faces = self._faces
            
            if self._verticesPerFace == 3:
                for i in range(0, faces.size, 3):
                    yield faces[i], faces[i+1], faces[i+2]
            else:
                for i in range(0, faces.size, 4):
                    yield faces[i], faces[i+1], faces[i+2], faces[i+3]
    
    
    def CalculateNormals(self):
        """ CalculateNormals()
        Calculate the normal data from the vertices.
        Triangular polygons are assumed.
        """
        
        # Get vertices as np array
        vertices = self._vertices
        if vertices is None:
            return
        
        # Init normal array
        N = vertices.shape[0]        
        normals = np.zeros((N,3), dtype='float32')
        defaultNormal = np.array([1,0,0], dtype='float32')
        
        # For all faces, calculate normals, and add to normals
        # If quads, we neglect the 4th vertex, which should be save, as it
        # should be in the same plane.
        for ii in self._IterFaces():
            v1 = vertices[ii[0],:]
            v2 = vertices[ii[1],:]
            v3 = vertices[ii[2],:]
            # Calculate normal
            tmp = np.cross(v1-v2,v2-v3)
            if np.isnan(tmp).sum():
                tmp = defaultNormal
            # Insert normals
            normals[ii[0],:] += tmp
            normals[ii[1],:] += tmp
            normals[ii[2],:] += tmp
        
        # Normalize normals
        for i in range(N):
            tmp = normals[i,:]
            tmp = tmp / ( (tmp**2).sum()**0.5 )
            if np.isnan(tmp).sum():
                tmp = defaultNormal
            normals[i,:] = -tmp
        
        # Store normals
        self._normals = normals
    
    
    
    def _CalculateFlatNormals(self):
        """ Calculate a variant of the normals that is more suited for 
        flat shading. This is done by setting the first normal for each
        face (the one used when flat shading is used) to the average
        of all normals of that face. This can in some cases lead to
        wrong results if a vertex is the first vertex of more than one
        face.
        """
        
        # If we want flad shading, we should not use faces
        self._WithoutFaces()
        
        # Get normals
        normals = self._normals
        if normals is None:
            return
        
        # Allocate new array
        N = normals.shape[0]        
        flatNormals = np.zeros((N,3), dtype='float32')
        
        # Sum all normals belonging to one face
        verticesPerFace = float(self._verticesPerFace)
        a, b = set(), list()
        for ii in self._IterFaces():
            i0 = ii[-1]
            a.add(i0)
            b.append(i0)
            for i in ii:
                flatNormals[i0,:] += normals[i,:] / verticesPerFace
        print len(a), len(b)
#         # Normalize normals
#         defaultNormal = np.array([1,0,0], dtype='float32')
#         for i in range(N):
#             tmp = flatNormals[i,:]
#             tmp = tmp / ( (tmp**2).sum()**0.5 )
#             if np.isnan(tmp).sum():
#                 tmp = defaultNormal
#             flatNormals[i,:] = tmp
        
        # Store
        self._flatNormals = flatNormals


if __name__ == '__main__':
    import visvis as vv
    a = vv.cla()
    a.daspectAuto = False
    a.cameraType = '3d'
    a.SetLimits((-2,2),(-2,2),(-2,2))
    
    #p = vv.solidTeapot()
    #p = vv.polygon.getCube(a)
    p = vv.solidSphere(2,None, 50,50)
    im = vv.imread('lena.png')
    p.SetTexture(im)

    p.Draw()
    a.SetLimits()
    