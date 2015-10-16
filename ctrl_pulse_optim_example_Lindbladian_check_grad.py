# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 15:12:53 2014
@author: Alexander Pitchford
@email1: agp1@aber.ac.uk
@email2: alex.pitchford@gmail.com
@organization: Aberystwyth University
@supervisor: Daniel Burgarth

Example to demonstrate using the control library to determine control
pulses using the ctrlpulseoptim.optimize_pulse function.
The (default) L-BFGS-B algorithm is used to optimise the pulse to
minimise the fidelity error, which in this case is given by the
'Trace difference' norm.

This in an open quantum system example, with a single qubit subject to
an amplitude damping channel. The target evolution is the Hadamard gate.
The user can experiment with the strength of the amplitude damping by
changing the gamma variable value

The user can experiment with the timeslicing, by means of changing the
number of timeslots and/or total time for the evolution.
Different initial (starting) pulse types can be tried.
The initial and final pulses are displayed in a plot

"""
import numpy as np
import numpy.matlib as mat
from numpy.matlib import kron
import matplotlib.pyplot as plt
import datetime
from scipy.optimize import check_grad

#QuTiP
from qutip import Qobj, identity, sigmax, sigmay, sigmaz, tensor
from qutip.qip import hadamard_transform
import qutip.logging_utils as logging
logger = logging.get_logger()
#QuTiP control modules
import qutip.control.pulseoptim as cpo

example_name = 'Lindblad'
log_level = logging.INFO

# ****************************************************************
# Define the physics of the problem
Sx = sigmax()
Sy = sigmay()
Sz = sigmaz()
Si = identity(2)

Sd = Qobj(np.array([[0, 1],
             [0, 0]]))
Sm = Qobj(np.array([[0, 0],
             [1, 0]]))
Sd_m = Qobj(np.array([[1, 0],
              [0, 0]]))
Sm_d = Qobj(np.array([[0, 0],
              [0, 1]]))

#Amplitude damping#
#Damping rate:
gamma = 0.1
L0_Ad = gamma*(2*tensor(Sm, Sd.trans()) - 
            (tensor(Sd_m, Si) + tensor(Si, Sd_m.trans())))
#sigma X control
LC_x = -1j*(tensor(Sx, Si) - tensor(Si, Sx))
#sigma Y control
LC_y = -1j*(tensor(Sy, Si) - tensor(Si, Sy.trans()))
#sigma Z control
LC_z = -1j*(tensor(Sz, Si) - tensor(Si, Sz))

#Drift
drift = L0_Ad
#Controls
ctrls = [LC_z, LC_x]
# Number of ctrls
n_ctrls = len(ctrls)

initial = identity(4)
#Target
#Hadamard gate
had_gate = hadamard_transform(1)
target_DP = tensor(had_gate, had_gate)

# ***** Define time evolution parameters *****
# Number of time slots
n_ts = 10
# Time allowed for the evolution
evo_time = 5

# ***** Define the termination conditions *****
# Fidelity error target
fid_err_targ = 1e-3
# Maximum iterations for the optisation algorithm
max_iter = 500
# Maximum (elapsed) time allowed in seconds
max_wall_time = 30
# Minimum gradient (sum of gradients squared)
# as this tends to 0 -> local minima has been found
min_grad = 1e-20

check_gradient = True

# Initial pulse type
# pulse type alternatives: RND|ZERO|LIN|SINE|SQUARE|SAW|TRIANGLE|
p_type = 'LIN'
# *************************************************************
# File extension for output files

f_ext = "{}_n_ts{}_ptype{}.txt".format(example_name, n_ts, p_type)

# Run the optimisation
print("\n***********************************")
print("Starting pulse optimisation")
# Note that this call will take the defaults
#    dyn_type='GEN_MAT'
# This means that matrices that describe the dynamics are assumed to be
# general, i.e. the propagator can be calculated using:
# expm(combined_dynamics*dt)
#    prop_type='FRECHET'
# and the propagators and their gradients will be calculated using the
# Frechet method, i.e. an exact gradent
#    fid_type='TRACEDIFF'
# and that the fidelity error, i.e. distance from the target, is give
# by the trace of the difference between the target and evolved operators 
optim = cpo.create_pulse_optimizer(drift, ctrls, initial, target_DP, 
                n_ts, evo_time, 
                fid_err_targ=fid_err_targ, min_grad=min_grad, 
                max_iter=max_iter, max_wall_time=max_wall_time, 
                init_pulse_type=p_type, 
                log_level=log_level, gen_stats=True)

dyn = optim.dynamics
p_gen = optim.pulse_generator
init_amps = np.zeros([n_ts, n_ctrls])
for j in range(n_ctrls):
    init_amps[:, j] = p_gen.gen_pulse()
        
dyn.initialize_controls(init_amps)

# Save initial amplitudes to a text file
pulsefile = "ctrl_amps_initial_" + f_ext
dyn.save_amps(pulsefile)
if (log_level <= logging.INFO):
    print("Initial amplitudes output to file: " + pulsefile)

if check_gradient: 
    print("***********************************")
    print("Checking gradient")
    func = optim.fid_err_func_wrapper
    grad = optim.fid_err_grad_wrapper
    x0 = dyn.ctrl_amps.flatten()
    grad_diff = check_grad(func, grad, x0)
    print("Normalised grad diff: {}".format(grad_diff))

print("***********************************")
print("Starting pulse optimisation")
result = optim.run_optimization()




print("***********************************")
print("\nOptimising complete. Stats follow:")
result.stats.report()
print("Final evolution\n{}\n".format(result.evo_full_final))

print("********* Summary *****************")
print("Final fidelity error {}".format(result.fid_err))
print("Terminated due to {}".format(result.termination_reason))
print("Number of iterations {}".format(result.num_iter))
#print("wall time: ", result.wall_time
print("Completed in {} HH:MM:SS.US".\
        format(datetime.timedelta(seconds=result.wall_time)))
# print("Final gradient normal {}".format(result.grad_norm_final)
print("***********************************")

# Plot the initial and final amplitudes
fig1 = plt.figure()
ax1 = fig1.add_subplot(2, 1, 1)
ax1.set_title("Initial ctrl amps")
ax1.set_xlabel("Time")
ax1.set_ylabel("Control amplitude")
t = result.time[:n_ts]
for j in range(n_ctrls):
    amps = result.initial_amps[:, j]
    ax1.plot(t, amps)
ax2 = fig1.add_subplot(2, 1, 2)
ax2.set_title("Optimised Control Sequences")
ax2.set_xlabel("Time")
ax2.set_ylabel("Control amplitude")
for j in range(n_ctrls):
    amps = result.final_amps[:, j]
    ax2.plot(t, amps)

plt.show()
