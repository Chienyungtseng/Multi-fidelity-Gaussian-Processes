"""
Bayesian Experimental Design Combining with Multi-fidelity co-Kriging
for Optimal Future Sample Locations in Upper Sangamon River Watershed (USRW)

Code by Chien-Yung Tseng, University of Illinois Urbana-Champaign
cytseng2@illinois.edu
"""

import numpy as np
import scipy as sp
import math
import matplotlib.pyplot as plt
import pandas as pd
import os
import scipy.stats as st

###############################################################################
# semivariance function for calculating the nugget, sill, and range in co-Kriging
###############################################################################
def dist(x1, x2):
    return np.sqrt(sum((x1-x2)**2))

def var(z1,z2):
    return (z1-z2)**2

def semivarf(Kdata,Xdata,Ydata,Zdata):
    K=Kdata.reshape(np.size(Kdata),-1)
    X=Xdata.reshape(np.size(Xdata),-1)
    Y=Ydata.reshape(np.size(Ydata),-1)
    Z=Zdata.reshape(np.size(Zdata),-1)
    loc=np.append(X,Y,axis=1)
    loc=np.append(loc,Z,axis=1)
    dis=np.zeros([len(K),len(K)])
    for i in range(len(K)):
        for j in range(i,len(K)):
            dis[i,j]=dist(loc[i,:],loc[j,:])
    semivar=np.zeros([len(K),len(K)])
    for i in range(len(K)):
        for j in range(i,len(K)):
            semivar[i,j]=0.5*var(K[i],K[j])
    semivar=semivar[np.where(dis != 0)]
    dis=dis[np.where(dis != 0)]
    for i in range(len(dis)):
        dis[i]=round(dis[i],0)
    semivar=semivar[np.where(dis != 0)]
    dis=dis[np.where(dis != 0)]
    
    df = pd.DataFrame([dis,semivar])
    df = df.transpose()
    mean = df.groupby(0).mean()
    dis = np.array(mean.index.values)
    semivar = mean.values[:,0]
    return dis, semivar
###############################################################################
###############################################################################
###############################################################################



###############################################################################
# EER Hydraulic Conductivity data #############################################
###############################################################################
# Read the depth-coord data
os.chdir('Data/EERdata')
name=os.listdir()
name.sort()
if name[0]=='.DS_Store':
    name.remove('.DS_Store') # Remove .DS_Store temp file in Mac OS
del name[-1]
n=len(name) # Number of data file

datalayers=50 # Number of layers for interpolating the measurement data
Z=np.empty([n,2])
for i in range(n):
    dataframe=pd.read_csv(name[i])
    data=dataframe.values
    Z[i,0]=min(pd.to_numeric(data[:,1], errors='coerce'))
    Z[i,1]=max(pd.to_numeric(data[:,1], errors='coerce'))
z_EER_min=max(Z[:,0])
z_EER_max=min(Z[:,1])

# Initiate raw dataset
Xdata=np.empty([datalayers,n])
Ydata=np.empty([datalayers,n])
Zdata=np.empty([datalayers,n])
Kdata=np.empty([datalayers,n])

# Construct Z and K data by data interpolation
from scipy.interpolate import NearestNDInterpolator
from scipy.interpolate import Rbf
for i in range(n):
    dataframe=pd.read_csv(name[i])
    data=dataframe.values
    x=pd.to_numeric(data[:,0], errors='coerce')
    z=pd.to_numeric(data[:,1], errors='coerce')   
    R=pd.to_numeric(data[:,2], errors='coerce')
    K=pd.to_numeric(data[:,3], errors='coerce')
    # Interpolation Grid
    meanx = np.mean(x)
    xrange = 50 # interpolation data range of x
    limz = np.array([(int(Z[i,0]/5)+1)*5,int(Z[i,1]/5)*5])
    resz = datalayers
    linz = np.linspace(limz[0], limz[1], resz)
    xint, zint = np.meshgrid(meanx, linz)
    ix=xint.reshape(-1,)
    iz=zint.reshape(-1,)
    # Scipy.interpolate.NearestNDInterpolator (nearest points)
    InterK= NearestNDInterpolator(np.transpose(np.array([x[abs(x-meanx)<xrange], z[abs(x-meanx)<xrange]])), K[abs(x-meanx)<xrange])
    Kint = InterK(np.transpose(np.array([ix,iz])))
    Kint = Kint.reshape(resz,-1)
    Zdata[:,i]=zint.transpose()
    Kdata[:,i]=Kint.transpose()

# Construct X and Y data
dataframe=pd.read_csv('z_coordinate.csv')
dataframe.sort_values(by=['ProfileName'], inplace=True)
data=dataframe.values
for i in range(n):
    Xdata[:,i]=pd.to_numeric(data[i,15], errors='coerce')
    Ydata[:,i]=pd.to_numeric(data[i,16], errors='coerce')

# Fit the semivariogram
from scipy.optimize import curve_fit
dis, semivar=semivarf(np.log(Kdata),Xdata,Ydata,Zdata*0.001)
s0 = 0.2
r0 = 10
n=(np.log(0.101)-np.log(0.1))**2
def gaus(dis,r,s):
    return (np.log(0.101)-np.log(0.1))**2+s*(1.-np.exp(-dis**2./(r*4./7.)**2.))
def expn(dis,r,s):
    return (np.log(0.101)-np.log(0.1))**2+s*(1.-np.exp(-dis/(r/3.)))
popt,pcov = curve_fit(expn,dis,semivar,p0=[r0,s0])
r=popt[0]
s=popt[1]
model_parameters_L=np.array([s, r, n])

fig, ax=plt.subplots(1, 1, figsize=(8, 5))
semiplot=plt.scatter(dis,semivar,20,c="w",marker='o', edgecolors='b', label="EER data")
plt.ylim([0,0.6])
plt.xlabel("distance (km)",fontsize=14)
plt.ylabel("semivariance ($cm^2$/$s^2$)",fontsize=14)
plt.grid()
dis_expn=np.linspace(0,60,100)
semiplot_expnreg=plt.plot(dis_expn,expn(dis_expn,r,s),color='red',linestyle='dashed',linewidth=2,label="Exponential Fitting")
plt.text(0,0.55,'Sill='+str(round(s,2)),fontsize=15)
plt.text(0,0.5,'Range='+str(round(r,2)),fontsize=15)
plt.text(0,0.45,'Nugget='+str(round(n,6)),fontsize=15)
legend = plt.legend(loc="upper right", fontsize=14)
for tick in ax.xaxis.get_major_ticks():
    tick.label.set_fontsize(14)
for tick in ax.yaxis.get_major_ticks():
    tick.label.set_fontsize(14)
plt.show()
os.chdir('../../')
fig.savefig('semivariance_EER.jpg', dpi=1200)

###############################################################################
# Low Fidelity Kriging Data ###################################################
###############################################################################
# Reshape X, Y, Z, K data
Xdata=Xdata.reshape(np.size(Xdata),-1)
Ydata=Ydata.reshape(np.size(Ydata),-1)
Zdata=Zdata.reshape(np.size(Zdata),-1)
Kdata=Kdata.reshape(np.size(Kdata),-1)
Xdata_L=np.concatenate([Xdata, Ydata, Zdata], axis=1)
Kdata_L=Kdata
###############################################################################
###############################################################################
###############################################################################



###############################################################################
# Pumping Test Hydraulic Conductivity data ####################################
###############################################################################
# Read data from .csv
os.chdir('Data/Pumpdata')
dataframe=pd.read_csv('Pumping_Test_Data.csv')
data=dataframe.values

# Initiate raw dataset
Xdata=pd.to_numeric(data[:,7], errors='coerce')
Ydata=pd.to_numeric(data[:,8], errors='coerce')
Z_top=pd.to_numeric(data[:,2], errors='coerce')*0.3048
Z_top[Z_top==0]=float("nan")
Zdata_depth=pd.to_numeric(data[:,1], errors='coerce')*0.3048
z_pump_max=np.nanmax(Zdata_depth)
z_pump_min=np.nanmin(Zdata_depth)
Zdata=Z_top-Zdata_depth
Kdata=pd.to_numeric(data[:,9], errors='coerce')*30.48/86400

Xdata = Xdata[~np.isnan(Zdata)]
Ydata = Ydata[~np.isnan(Zdata)]
Kdata = Kdata[~np.isnan(Zdata)]
Zdata_depth = Zdata_depth[~np.isnan(Zdata)]
Zdata = Zdata[~np.isnan(Zdata)]
Z_top = Z_top[~np.isnan(Z_top)]

# Fit the semivariogram
from scipy.optimize import curve_fit
dis, semivar=semivarf(np.log(Kdata),Xdata,Ydata,Zdata*0.001)
s0 = 1
r0 = 10
n=0
def gaus(dis,r,s):
    return 0+s*(1.-np.exp(-dis**2./(r*4./7.)**2.))
def expn(dis,r,s):
    return 0+s*(1.-np.exp(-dis/(r/3.)))
popt,pcov = curve_fit(expn,dis,semivar,p0=[r0,s0])
r=popt[0]
s=popt[1]
model_parameters_H=np.array([s, r, n])

fig, ax=plt.subplots(1, 1, figsize=(8, 5))
semiplot=plt.scatter(dis,semivar,20,c="w",marker='o', edgecolors='b', label="Pumping data")
plt.ylim([0,2])
plt.xlabel("distance (km)",fontsize=14)
plt.ylabel("semivariance ($cm^2$/$s^2$)",fontsize=14)
plt.grid()
dis_gaus=np.linspace(0,60,100)
semiplot_gaussreg=plt.plot(dis_gaus,expn(dis_gaus,r,s),color='red',linestyle='dashed',linewidth=2,label="Exponential Fitting")
plt.text(0,1.85,'Sill='+str(round(s,2)),fontsize=15)
plt.text(0,1.7,'Range='+str(round(r,2)),fontsize=15)
plt.text(0,1.55,'Nugget='+str(round(n,6)),fontsize=15)
legend = plt.legend(loc="upper right", fontsize=14)
for tick in ax.xaxis.get_major_ticks():
    tick.label.set_fontsize(14)
for tick in ax.yaxis.get_major_ticks():
    tick.label.set_fontsize(14)
plt.show()
os.chdir('../../')
fig.savefig('semivariance_Pump.jpg', dpi=1200)

###############################################################################
# High Fidelity Kriging Data ##################################################
###############################################################################
# Reshape X, Y, Z, K data
Xdata=Xdata.reshape(np.size(Xdata),-1)
Ydata=Ydata.reshape(np.size(Ydata),-1)
Zdata=Zdata.reshape(np.size(Zdata),-1)
Zdata_depth=Zdata_depth.reshape(np.size(Zdata_depth),-1)
Kdata=Kdata.reshape(np.size(Kdata),-1)
Xdata_H=np.concatenate([Xdata, Ydata, Zdata_depth], axis=1)
Kdata_H=Kdata
###############################################################################
###############################################################################
###############################################################################



###############################################################################
# Specify region domain #######################################################
###############################################################################
limx = np.array([-40, 10])
limy = np.array([-15, 30])
limz = np.array([(int(min(min(Xdata_L[:,2]),min(Xdata_H[:,2]))/5)+1)*5,(int(max(max(Xdata_L[:,2]),max(Xdata_H[:,2]))/5)-1)*5])

Kdata_H_region=Kdata_H[Xdata_H[:,0]>=limx[0],:]
Zdata_depth_region=Zdata_depth[Xdata_H[:,0]>=limx[0]]
Xdata_H_region=Xdata_H[Xdata_H[:,0]>=limx[0],:]
Kdata_H_region=Kdata_H_region[Xdata_H_region[:,0]<=limx[1],:]
Zdata_depth_region=Zdata_depth_region[Xdata_H_region[:,0]<=limx[1]]
Xdata_H_region=Xdata_H_region[Xdata_H_region[:,0]<=limx[1],:]
Kdata_H_region=Kdata_H_region[Xdata_H_region[:,1]>=limy[0],:]
Zdata_depth_region=Zdata_depth_region[Xdata_H_region[:,1]>=limy[0]]
Xdata_H_region=Xdata_H_region[Xdata_H_region[:,1]>=limy[0],:]
Kdata_H_region=Kdata_H_region[Xdata_H_region[:,1]<=limy[1],:]
Zdata_depth_region=Zdata_depth_region[Xdata_H_region[:,1]<=limy[1]]
Xdata_H_region=Xdata_H_region[Xdata_H_region[:,1]<=limy[1],:]
Kdata_L_region=Kdata_L[Xdata_L[:,0]>=limx[0],:]
Xdata_L_region=Xdata_L[Xdata_L[:,0]>=limx[0],:]
Kdata_L_region=Kdata_L_region[Xdata_L_region[:,0]<=limx[1],:]
Xdata_L_region=Xdata_L_region[Xdata_L_region[:,0]<=limx[1],:]
Kdata_L_region=Kdata_L_region[Xdata_L_region[:,1]>=limy[0],:]
Xdata_L_region=Xdata_L_region[Xdata_L_region[:,1]>=limy[0],:]
Kdata_L_region=Kdata_L_region[Xdata_L_region[:,1]<=limy[1],:]
Xdata_L_region=Xdata_L_region[Xdata_L_region[:,1]<=limy[1],:]
###############################################################################
###############################################################################
###############################################################################



###############################################################################
# Multi-Fidelity co-Kriging ###################################################
###############################################################################
# Kriging's Grid
dz = 15
layers = int(round(abs(limz[0]-limz[1])/dz+0.0001,0))
resx = 200
resy = 200
resz = layers
linx = np.linspace(limx[0], limx[1], resx)
liny = np.linspace(limy[0], limy[1], resy)
linz = np.arange(limz[0], limz[1], dz)
linz = linz+dz/2
yy, zz, xx = np.meshgrid(liny, linz, linx)

from multifidgp.multikriging import MultiKriging
import numpy_indexed as npi
    
# Determine the data
k = 4 # specify the layer
HXdata=Xdata_H_region[abs(Xdata_H_region[:,2]-round(linz[k],2))<=0.5*dz,0:2]
HKdata=Kdata_H_region[abs(Xdata_H_region[:,2]-round(linz[k],2))<=0.5*dz,0:2]
LXdata=Xdata_L_region[abs(Xdata_L_region[:,2]-round(linz[k],2))<=0.5*dz,0:2]
LKdata=Kdata_L_region[abs(Xdata_L_region[:,2]-round(linz[k],2))<=0.5*dz,0:2]    
index=np.argsort(LXdata[:,0])
LXdata=LXdata[index,:]
LKdata=LKdata[index,:]
Ldata=np.concatenate([LXdata, LKdata], axis=1)
Group=npi.group_by(Ldata[:, 0]).mean(Ldata)
Result=Group[1]
LXdata=Result[:,0:2]
LKdata=Result[:,2]
LKdata=LKdata.reshape(np.size(LKdata),-1)

MultiKrig = MultiKriging(HXdata, np.log(HKdata), LXdata, np.log(LKdata),
                                        model_parameters_H, model_parameters_L)
Cond_Krig, sigmas = MultiKrig.execute2D(xx[k,:,:], yy[k,:,:])
       
# Convert the result from lognormal scale back to the normal scale 
logCond_Krig = np.exp(Cond_Krig + 0.5*sigmas)
logsigmas = (np.exp(sigmas)-1)*np.exp(2*Cond_Krig+sigmas)

print(np.max(logCond_Krig))
print(np.mean(logCond_Krig))

refz = linz[k]*np.ones([resx,resy])
Cond_K = logCond_Krig
sigma = logsigmas
###############################################################################
###############################################################################
###############################################################################



###############################################################################
# Bayesian Experimental Design ################################################
###############################################################################
from multifidgp.multibayesian_exp import MultiBayesianExp
# specify the optimal coefficient rho from Multi-fidelity co-Kriging
rho = np.array([0.8826643, 3.47407575, 4.60907016, 0.36591023, 0.19213686])
pts = 5 # how many suggestion points
f = np.ones(pts) # 0 for low-fidelity point; 1 for high-fidelity point
inipt = np.zeros([pts,3],dtype=float)
newpt = np.zeros([pts,3],dtype=float)

HXdata_Bay = HXdata
LXdata_Bay = LXdata
HKdata_Bay = HKdata
LKdata_Bay = LKdata

# define the sampling domain and sampling resolution
bndx = np.array([-30, 5])
bndy = np.array([-10, 20])
bnd = np.concatenate([bndx, bndy], axis=0)
bnd = bnd.reshape([-1,2])
res = 1

for n in range(pts):
    print("Calculating sequential sampling point ", n+1)       
    Bayesian = MultiBayesianExp(HXdata_Bay, LXdata_Bay, HKdata_Bay, LKdata_Bay,
                                model_parameters_H, model_parameters_L, rho[k])
    inis=np.array([np.random.uniform(-35,5), np.random.uniform(-10,25)])
    inipt[n,:]=np.array([inis[0],inis[1],f[n]])
    s = Bayesian.execute_max(bnd, res)
    if f[n]==0:
        LXdata_Bay=np.concatenate([LXdata_Bay, np.array([s])], axis=0)
        LKdata_Bay=np.concatenate([LKdata_Bay, np.array([Bayesian.MultiKrig(s, model_parameters_H[1], model_parameters_L[1])[0]])], axis=0)
        newpt[n,:]=np.array([s[0],s[1],f[n]])
    elif f[n]==1:
        HXdata_Bay=np.concatenate([HXdata_Bay, np.array([s])], axis=0)
        HKdata_Bay=np.concatenate([HKdata_Bay, np.array([Bayesian.MultiKrig(s, model_parameters_H[1], model_parameters_L[1])[0]])], axis=0)
        newpt[n,:]=np.array([s[0],s[1],f[n]])

newpt_L=newpt[newpt[:,2]==0,:]
newpt_H=newpt[newpt[:,2]==1,:]
print('Initial Points = ')
print(inipt)
print('Suggested Points = ')
print(newpt)

fig, ax = plt.subplots(2, 1, figsize=(6, 8))
h=ax[0].pcolor(xx[k,:,:],yy[k,:,:],Cond_K,cmap='Spectral_r', vmin=0, vmax=0.16)
ax[0].plot(HXdata[:,0], HXdata[:,1], c='b', marker='o', markersize=8, fillstyle='none', linestyle='none', label='High-fidelity Data')
ax[0].plot(LXdata[:,0], LXdata[:,1], c='k', marker='x', markersize=8, fillstyle='none', linestyle='none', label='Low-fidelity Data')
cbar=fig.colorbar(h,ax=ax[0])
cbar.ax.get_yaxis().labelpad = 15
cbar.ax.tick_params(labelsize=14)
cbar.ax.set_ylabel('Conductivity K (cm/s)', rotation=270, fontsize=14)
figname="k = "+str(k+1)+" (depth = "+str(round(linz[k],2))+"m )"
ax[0].set_title(figname, fontsize=16)
ax[0].set_ylabel("y (km)", fontsize=14)
ax[0].set_xlim(limx[0], limx[1])
ax[0].set_ylim(limy[0], limy[1])
for tick in ax[0].xaxis.get_major_ticks():
    tick.label.set_fontsize(14)
for tick in ax[0].yaxis.get_major_ticks():
    tick.label.set_fontsize(14)
    
h=ax[1].pcolor(xx[k,:,:],yy[k,:,:],np.sqrt(sigma),cmap='Spectral_r', vmin=0, vmax=0.8) # specified method top
ax[1].plot(HXdata[:,0], HXdata[:,1], c='b', marker='o', markersize=8, fillstyle='none', linestyle='none', label='High-fidelity Data')
ax[1].plot(LXdata[:,0], LXdata[:,1], c='k', marker='x', markersize=8, fillstyle='none', linestyle='none', label='Low-fidelity Data')
cbar=fig.colorbar(h,ax=ax[1])
cbar.ax.get_yaxis().labelpad = 15
cbar.ax.tick_params(labelsize=14)
cbar.ax.set_ylabel(r'$\sigma (cm/s)$', rotation=270, fontsize=14)
ax[1].set_xlabel("x (km)", fontsize=14)
ax[1].set_ylabel("y (km)", fontsize=14)
ax[1].set_xlim(limx[0], limx[1])
ax[1].set_ylim(limy[0], limy[1])
for tick in ax[1].xaxis.get_major_ticks():
    tick.label.set_fontsize(14)
for tick in ax[1].yaxis.get_major_ticks():
    tick.label.set_fontsize(14)

figname2="Current Result"
fig.savefig(figname2, dpi=1200)

HXdata_Bay = HXdata
LXdata_Bay = LXdata
HKdata_Bay = HKdata
LKdata_Bay = LKdata
HXdata_Bay2 = HXdata
LXdata_Bay2 = LXdata
HKdata_Bay2 = HKdata
LKdata_Bay2 = LKdata
for n in range(pts):
    from multifidgp.multikriging import MultiKriging
    Bayesian = MultiBayesianExp(HXdata_Bay, LXdata_Bay, HKdata_Bay, LKdata_Bay,
                                model_parameters_H, model_parameters_L, rho[k])
    HXdata_Bay2=np.concatenate([HXdata_Bay2, np.array([newpt_H[-pts+n,0:2]])], axis=0)
    HKdata_Bay2=np.concatenate([HKdata_Bay2, np.array([Bayesian.MultiKrig(newpt_H[-pts+n,0:2], model_parameters_H[1], model_parameters_L[1])[0]])], axis=0)
    MultiKrig2 = MultiKriging(HXdata_Bay2, np.log(HKdata_Bay2), LXdata_Bay2, np.log(LKdata_Bay2),
                                        model_parameters_H, model_parameters_L)
    Cond_Krig2D, sigmas2D = MultiKrig2.MultiKrig2D(xx[k,:,:], yy[k,:,:], rho[k])
    # Convert the result from lognormal scale back to the normal scale 
    Cond_K = np.exp(Cond_Krig2D + 0.5*sigmas2D)
    sigma = (np.exp(sigmas2D)-1)*np.exp(2*Cond_Krig2D+sigmas2D)
    
    fig, ax = plt.subplots(2, 1, figsize=(6, 8))
    h=ax[0].pcolor(xx[k,:,:],yy[k,:,:],Cond_K,cmap='Spectral_r', vmin=0, vmax=0.16)
    ax[0].plot(HXdata[:,0], HXdata[:,1], c='b', marker='o', markersize=8, fillstyle='none', linestyle='none', label='High-fidelity Data')
    ax[0].plot(LXdata[:,0], LXdata[:,1], c='k', marker='x', markersize=8, fillstyle='none', linestyle='none', label='Low-fidelity Data')
    ax[0].plot(newpt[:n+1,0], newpt[:n+1,1], c='r', marker='^', markersize=8, fillstyle='none', linestyle='none', label='Suggested Future Samplings')
    cbar=fig.colorbar(h,ax=ax[0])
    cbar.ax.get_yaxis().labelpad = 15
    cbar.ax.tick_params(labelsize=14)
    cbar.ax.set_ylabel('Conductivity K (cm/s)', rotation=270, fontsize=14)
    figname="k = "+str(k+1)+" (depth = "+str(round(linz[k],2))+"m )"
    ax[0].set_title(figname, fontsize=16)
    ax[0].set_ylabel("y (km)", fontsize=14)
    ax[0].set_xlim(limx[0], limx[1])
    ax[0].set_ylim(limy[0], limy[1])
    for tick in ax[0].xaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    for tick in ax[0].yaxis.get_major_ticks():
        tick.label.set_fontsize(14)
        num = np.linspace(range(pts)[0]+1, range(pts)[pts-1]+1, pts, dtype=int)
        text1 = num.astype('str')
        font = {'family': 'serif',
                'color':  'red',
                'weight': 'normal',
                'size': 14,
                }
    for i in range(n+1):
        plt.text(newpt[i,0]+0.5, newpt[i,1]+0.5, text1[i], fontdict=font)

    h=ax[1].pcolor(xx[k,:,:],yy[k,:,:],np.sqrt(sigma),cmap='Spectral_r', vmin=0, vmax=0.8) # specified method top
    ax[1].plot(HXdata[:,0], HXdata[:,1], c='b', marker='o', markersize=8, fillstyle='none', linestyle='none', label='High-fidelity Data')
    ax[1].plot(LXdata[:,0], LXdata[:,1], c='k', marker='x', markersize=8, fillstyle='none', linestyle='none', label='Low-fidelity Data')
    ax[1].plot(newpt[:n+1,0], newpt[:n+1,1], c='r', marker='^', markersize=8, fillstyle='none', linestyle='none', label='Suggested Future Samplings')
    cbar=fig.colorbar(h,ax=ax[1])
    cbar.ax.get_yaxis().labelpad = 15
    cbar.ax.tick_params(labelsize=14)
    cbar.ax.set_ylabel(r'$\sigma (cm/s)$', rotation=270, fontsize=14)
    ax[1].set_xlabel("x (km)", fontsize=14)
    ax[1].set_ylabel("y (km)", fontsize=14)
    ax[1].set_xlim(limx[0], limx[1])
    ax[1].set_ylim(limy[0], limy[1])
    for tick in ax[1].xaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    for tick in ax[1].yaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    num = np.linspace(range(pts)[0]+1, range(pts)[pts-1]+1, pts, dtype=int)
    text1 = num.astype('str')
    font = {'family': 'serif',
            'color':  'red',
            'weight': 'normal',
            'size': 14,
            }
    for i in range(n):
        plt.text(newpt[i,0]+0.5, newpt[i,1]+0.5, text1[i], fontdict=font)

    figname2="plus future point " + str(n+1)
    fig.savefig(figname2, dpi=1200)
###############################################################################
###############################################################################
###############################################################################