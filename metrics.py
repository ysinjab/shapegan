from model.sdf_net import SDFNet, LATENT_CODE_SIZE
import numpy as np
from util import device, standard_normal_distribution
from tqdm import tqdm
import sys
import torch
import skimage
import trimesh

def rescale_point_cloud(point_cloud, method=None):
    if method == 'half_unit_sphere':
        point_cloud /= np.linalg.norm(point_cloud, axis=1).max() * 2
    elif method == 'half_unit_cube':
        point_cloud /= np.abs(point_cloud).max() * 2

def sample_point_clouds(sdf_net, sample_count, point_cloud_size, voxel_resolution=128, rescale='half_unit_sphere'):
    result = np.zeros((sample_count, point_cloud_size, 3))
    latent_codes = standard_normal_distribution.sample((sample_count, LATENT_CODE_SIZE)).to(device)
    for i in tqdm(range(sample_count)):
        point_cloud = sdf_net.get_uniform_surface_points(latent_codes[i, :], point_count=point_cloud_size, voxel_resolution=voxel_resolution, sphere_only=False)
        rescale_point_cloud(point_cloud, method=rescale)
        result[i, :, :] = point_cloud
    return result

def sample_from_voxels(voxels, point_cloud_size, rescale='half_unit_sphere'):
    result = np.zeros((voxels.shape[0], point_cloud_size, 3))
    size = 2
    voxel_resolution = voxels.shape[1]
    for i in tqdm(range(voxels.shape[0])):
        voxels_current = voxels[i, :, :, :]
        voxels_current = np.pad(voxels_current, 1, mode='constant', constant_values=1)
        
        vertices, faces, normals, _ = skimage.measure.marching_cubes_lewiner(voxels_current, level=0, spacing=(size / voxel_resolution, size / voxel_resolution, size / voxel_resolution))
        vertices -= size / 2
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_normals=normals)
        point_cloud = mesh.sample(point_cloud_size)
        rescale_point_cloud(point_cloud, method=rescale)
        result[i, :, :] = point_cloud
    return result


if 'sample' in sys.argv:
    sdf_net = SDFNet()
    sdf_net.filename = 'hybrid_gan_generator.to'
    sdf_net.load()
    sdf_net.eval()

    clouds = sample_point_clouds(sdf_net, 1000, 1000, voxel_resolution=32)
    np.save('data/generated_point_cloud_sample.npy', clouds)

if 'dataset' in sys.argv:
    voxels = torch.load('data/chairs-voxels-32.to').detach().cpu().numpy()[:1000, :, :, :]
    clouds = sample_from_voxels(voxels, 1000)
    np.save('data/dataset_point_cloud_sample.npy', clouds)


if 'test' in sys.argv:
    import pyrender
    data = np.load('data/dataset_point_cloud_sample.npy')
    for i in range(data.shape[0]):
        points = data[i, :, :]
        scene = pyrender.Scene()
        scene.add(pyrender.Mesh.from_points(points))
        pyrender.Viewer(scene, use_raymond_lighting=True, point_size=8)