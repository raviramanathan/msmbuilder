#!/usr/bin/env python
 
from msmbuilder import arglib
from msmbuilder import Project
from msmbuilder import Trajectory
from msmbuilder import io
from msmbuilder.reduce.tICA import tICA
import numpy as np
import os, sys, re
import scipy
import logging
logger = logging.getLogger('msmbuilder.scripts.tICA_train')

def run(prep_metric, project, delta_time, atom_indices=None, 
        output='tICAData.h5', min_length=0, stride=1):

    # We will load the trajectories at the stride, so we need to find
    # what dt should be once we've strided by some amount
    lag = delta_time / stride
    
    if (float(delta_time) / stride) != lag:
        raise Exception("Stride must be a divisor of delta_time.")

    if lag > 0: # Then we're doing tICA
        tica_obj = tICA(lag=lag, calc_cov_mat=True, prep_metric=prep_metric)
    else: # If lag is zero, this is equivalent to regular PCA
        tica_obj = tICA(lag=lag, calc_cov_mat=False, prep_metric=prep_metric)
    
    for i in xrange(project.n_trajs):
        logger.info("Working on trajectory %d" % i)

        if project.traj_lengths[i] <= lag:
            logger.info("Trajectory is not long enough for this lag "
                        "(%d vs %d)", project.traj_lengths[i], lag)
            continue

        if project.traj_lengths[i] < min_length:
            logger.info("Trajectory is not longer than min_length "
                        "(%d vs %d)", project.traj_lengths[i], min_length)
            continue

        for traj_chunk in Trajectory.enum_chunks_from_lhdf(project.traj_filename(i),
                Stride=stride, AtomIndices=atom_indices):

            tica_obj.train(trajectory=traj_chunk)

    tica_obj.solve()
    tica_obj.save(output)
    logger.info("Saved output to %s", output)

    return tica_obj


if __name__ == '__main__':
    parser = arglib.ArgumentParser(get_basic_metric=True, 
        description="""tICA_train.py is used to calculate the time-lag
        correlation and covariance matrices for use in the tICA metric.
        This method attempts to find projection vectors such that they
        have a maximal autocorrelation function.
        
        For more details see:
        Schwantes, CR and Pande, VS. J. Chem. Theory Comput., 2013, 9 (4),
            pp 2000-2009. DOI: 10.1021/ct300878a
        """)
    parser.add_argument('project')
    parser.add_argument('stride', type=int, default=1, 
        help='stride to subsample input trajectories')
    parser.add_argument('atom_indices', default='all',
        help='atom indices to restrict trajectories to')
    parser.add_argument('output', default='tICAData.h5',
        help='output filename to save results to')
    parser.add_argument('delta_time', type=int, help="""delta time to 
        use in calculating the time-lag correlation matrix""")
    parser.add_argument('min_length', type=int, default=0, 
        help="""only train on trajectories greater than <min_length> 
        number of frames""")
    
    args, prep_metric = parser.parse_args()
    
    arglib.die_if_path_exists(args.output)
    
    if args.atom_indices.lower() == 'all':
        atom_indices = None
    else:
        atom_indices = np.loadtxt(args.atom_indices).astype(int)
   
    project = Project.load_from(args.project)
    min_length = int(float(args.min_length)) 
    # need to convert to float first because int can't 
    # convert a string that is '1E3' for example...weird.

    tica_obj = run(prep_metric, project, args.delta_time, atom_indices=atom_indices, 
        output=args.output, min_length=min_length, stride=args.stride)

