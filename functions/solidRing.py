import visvis as vv
import numpy as np
from visvis.points import Point, Pointset

import OpenGL.GL as gl


def solidRing(translation=None, scale=None, thickness=0.4, N=16, M=16, axes=None):
    """ solidRing(translation=None, scale=None, thickness=0.1, N=16, M=16, axes=None)
    
    Creates a solid ring with quad faces. N is the number of faces along
    the ring, M is the number of faces around the tube that makes up the
    ring.
    """
    
    # Note that the number of vertices around the axis is slices+1. This
    # would not be necessary per see, but it helps create a nice closed
    # texture when it is mapped. There are slices number of faces though.
    # Similarly, to obtain stacks faces along the axis, we need stacks+1
    # vertices.
    
    # Check position
    if isinstance(translation, tuple):
        translation = Point(translation)
    
    # Quick access
    pi = np.pi
    pi2 = np.pi*2
    cos = np.cos
    sin = np.sin
    sl = M+1
    
    # Determine where the stitch is, depending on M
    if M<=8:
        rotOffset = 0.5/M
    else:
        rotOffset = 0.0
    
    # Calculate vertices, normals and texcords
    vertices = Pointset(3)
    normals = Pointset(3)
    texcords = Pointset(2)
    # Cone
    for n in range(N+1):
        v = float(n)/N
        a = pi2 * v        
        # Obtain outer and center position of "tube"
        po = Point(sin(a), cos(a), 0)
        pc = po * (1.0-0.5*thickness)
        # Create two vectors that span the the circle orthogonal to the tube
        p1 = (pc-po)
        p2 = Point(0, 0, 0.5*thickness)
        # Sample around tube        
        for m in range(M+1):
            u = float(m) / (M)
            b = pi2 * (u+rotOffset) 
            dp = cos(b) * p1 + sin(b) * p2
            vertices.Append(pc+dp)
            normals.Append(dp.Normalize())
            texcords.Append(v,u)
    
    # Calculate indices
    indices = []
    for j in range(N):
        for i in range(M):
            indices.extend([j*sl+i, j*sl+i+1, (j+1)*sl+i+1, (j+1)*sl+i])
    
    # Make indices a numpy array
    indices = np.array(indices, dtype=np.uint32)
    
    
    # Create axes 
    if axes is None:
        axes = vv.gca()
    
    # Create mesh
    m = vv.Mesh(axes, vertices, normals, indices, 
        texcords=texcords, verticesPerFace=4)
    
#     # If necessary, use flat shading
#     if N<=8 or M<=8:
#         pass # todo: set flat shading

    # Scale and translate
    if translation is not None:
        tt = vv.Transform_Translate(translation.x, translation.y, translation.z)    
        m.transformations.append(tt)
    
    # Done
    return m


if __name__ == '__main__':
    import visvis as vv
    app = vv.use('qt4')
    a = vv.cla()
    a.daspectAuto = False
    a.cameraType = '3d'    
    
    # Create ring
    m = solidRing((1,1,1), thickness=0.4, M=4)
    im = vv.imread('lena.png')
    m.SetTexture(im)
    a.SetLimits()#((-2,2),(-2,2),(-2,2))
    m.Draw()
    
#     data = np.linspace(0,1,m._vertices.shape[0])
#     m.SetTexcords(data.astype(np.float32))
