import re
from scipy.interpolate import interp1d

import numpy as np
from scipy.optimize import curve_fit
from scipy import signal
from scipy import stats
import peakutils
import matplotlib.pyplot as plt
from numba import jit
from scipy import ndimage


@jit(nopython=True)
def lockin_filter(signal, reference):
    width = signal.shape[0]
    y = np.zeros(width)
    for ind in range(width):
        y[ind] = np.sum(signal[ind,:] * reference) / len(reference)

    return y

@jit()
def interpolate_data(x,x_new,signal):
    width = signal.shape[0]
    res = np.zeros((signal.shape[0],len(x_new)))
    for ind in range(width):
        spline = interp1d(x, signal[ind, :], kind='cubic')
        res[ind, :] = spline(x_new)
    return res


def plot_lockin(wl,series,savedir):
    ts = series[1:, :]
    t = series[0, :]

    maxwl = 1000
    minwl = 400
    mask = (wl >= minwl) & (wl <= maxwl)

    n = ts.shape[1]
    width = ts.shape[0]
    t2 = np.linspace(0, t.max(), n*5)

    for ind in range(width):
        slope, intercept, r_value, p_value, std_err = stats.linregress(t, ts[ind,:])
        ts[ind, :] -= slope*t+intercept

    ts = ndimage.median_filter(ts, 7)
    plt.imshow(ts.T, extent=(wl.min(), wl.max(), t2.max(), t2.min()), aspect=1,cmap=plt.get_cmap("seismic"))
    plt.xlabel("Wavelength / nm")
    plt.ylabel("t / s")
    #plt.show()
    plt.savefig(savedir + "signal_filt.png",dpi=400)
    plt.close()

    ts = interpolate_data(t,t2,ts)


    @jit()
    def func(x,a,f,p,c):
        return a*np.sin(2 * np.pi * x * f + p) + c

    res = np.zeros(width)
    res_phase = np.zeros(width)
    freqs = np.zeros(width)
    for ind in range(width):
        print(ind)
        fft = np.fft.rfft(ts[ind,:],norm="ortho")
        d = np.absolute(fft)
        p = np.angle(fft)
        res[ind] = d[1:].max()
        res_phase[ind] = p[d[1:].argmax()+1]

        f_buf = np.fft.rfftfreq(t2.shape[0], d=t2[1] - t2[0])
        freqs[ind] = f_buf[d[1:].argmax()+1]

    freqs = freqs
    freqs = freqs[np.argwhere(res > np.max(res)*0.9)]
    freqs = freqs[:,0]
    freqs = freqs[np.argwhere(freqs > 0)]
    print(freqs.shape)

    res_phase += np.pi
    phase = res_phase[np.argmax(res)]

    f = freqs[0]
    print(f)

    maxind = np.argmax(res)
    y = ts[maxind, :]

    fft = np.fft.rfft(y, norm="ortho")
    d = np.absolute(fft)
    p = np.angle(fft)
    f_buf = np.fft.rfftfreq(t2.shape[0], d=t2[1] - t2[0])
    print(f_buf[d[1:].argmax()])

    initial_guess = [y.max() - y.min(), f, 0, np.mean(y)]
    popt, pcov = curve_fit(func, t2, y, p0=initial_guess)

    fig = plt.figure()
    plt.plot(t2,y)
    plt.plot(t2,func(t2,popt[0],popt[1],popt[2],popt[3]))
    plt.savefig(savedir + "fit.png",dpi=300)
    plt.close()

    f = popt[1]
    phase = popt[2]
    print(f)

    fig = plt.figure()
    ax = fig.add_subplot(111)
    res_phase = res_phase * 180/np.pi
    p1 = ax.plot(wl[mask], res[mask], alpha=0.5)  # /lamp[mask])
    res2 = signal.savgol_filter(res, 71, 1)
    p2 = ax.plot(wl[mask], res2[mask])  # /lamp[mask])
    ax.tick_params('y', colors=p2[0].get_color())

    ax2 = ax.twinx()

    next(ax2._get_lines.prop_cycler)
    next(ax2._get_lines.prop_cycler)

    p3 = ax2.plot(wl[mask], res_phase[mask], alpha=0.5)  # /lamp[mask])
    ax2.tick_params('y', colors=p3[0].get_color())

    ax.set_zorder(ax2.get_zorder() + 1)  # put ax in front of ax2
    ax.patch.set_visible(False)  # hide the 'canvas'

    plt.savefig(savedir + "lockin_fft.png",dpi=300)
    plt.close()

    ref = np.sin(2 * np.pi * t2 * f)
    ref2 = np.sin(2 * np.pi * t2 * f + np.pi/2)

    x2 = lockin_filter(ts,ref)
    y2 = lockin_filter(ts,ref2)

    res_amp = np.abs(x2 + 1j * y2)
    res_phase = np.angle(x2 + 1j * y2)
    maxind = np.argmax(signal.savgol_filter(res_amp, 71, 1))
    phase = res_phase[maxind]
    print("phase1: "+str(phase))

    phases = np.linspace(0,2*np.pi,3600)
    x1 = np.zeros(len(phases))
    for i in range(len(phases)):
        ref1 = np.sin(2 * np.pi * t2 * f + phases[i])
        x1[i] = lockin_filter(np.matrix(ts[maxind,:]),ref1)

    phase = phases[np.argmax(x1)]
    print("phase2: "+str(phase))

    res_phase = np.angle( (x2*np.cos(phase)-y2*np.sin(phase)) + 1j * ( x2*np.sin(phase) + y2*np.cos(phase) ))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(t2, ref / np.max(ref) + 0)
    ax.plot(t2, ref2 / np.max(ref2) + 1)

    indices = [np.argmin(np.abs(wl - 500)), np.argmin(np.abs(wl - 600)), np.argmin(np.abs(wl - 700)),
               np.argmin(np.abs(wl - 810))]
    for i, ind in enumerate(indices):
        buf = ts[ind,:]
        buf = buf - np.min(buf)
        ax.plot(t2, buf / np.max(buf) + i + 2)

    plt.savefig(savedir + "traces.png",dpi=300)
    plt.close()

    fig = plt.figure()
    ax = fig.add_subplot(111)
    indices = [np.argmin(np.abs(wl - 500)), np.argmin(np.abs(wl - 600)), np.argmin(np.abs(wl - 700)),
               np.argmin(np.abs(wl - 810))]
    for i, ind in enumerate(indices):

        fft = np.fft.rfft(ts[ind,:])
        d = np.absolute(fft)
        p = np.abs(np.angle(fft))
        f_buf = np.fft.rfftfreq(t2.shape[0])
        blub = int(len(f_buf)/4)
        ax.plot(f_buf[1:blub], d[1:blub] / d[1:blub].max() + i)
        ax.plot(f_buf[1:blub], p[1:blub] / p[1:blub].max() + i, alpha=0.5)

    plt.savefig(savedir + "fft.png",dpi=300)
    plt.close()


    fig = plt.figure()
    ax = fig.add_subplot(111)
    res_phase = res_phase * 180/np.pi
    p1 = ax.plot(wl[mask], res_amp[mask], alpha=0.5)
    res2 = signal.savgol_filter(res_amp, 71, 1)
    p2 = ax.plot(wl[mask], res2[mask])
    ax.tick_params('y', colors=p2[0].get_color())
    ax2 = ax.twinx()
    next(ax2._get_lines.prop_cycler)
    next(ax2._get_lines.prop_cycler)
    p3 = ax2.plot(wl[mask], res_phase[mask], alpha=0.5)
    ax2.tick_params('y', colors=p3[0].get_color())

    ax.set_zorder(ax2.get_zorder() + 1)  # put ax in front of ax2
    ax.patch.set_visible(False)  # hide the 'canvas'

    plt.savefig(savedir + "lockin_nopsd.png",dpi=300)
    plt.close()


    ref = np.sin(2 * np.pi * t2 * f + phase)
    ref2 = np.sin(2 * np.pi * t2 * f  + phase - np.pi)

    if dir == "B1":
        x2 = lockin_filter(ts,ref)
        x1 = lockin_filter(ts,ref2)
    else:
        x1 = lockin_filter(ts,ref)
        x2 = lockin_filter(ts,ref2)

    x1[x1 <0]  = 0
    x2[x2 < 0] = 0

    fig = plt.figure()
    ax = fig.add_subplot(111)

    p1 = ax.plot(wl[mask], x1[mask], alpha=0.5)  # /lamp[mask])
    res2 = signal.savgol_filter(x1, 71, 1)
    p2 = ax.plot(wl[mask], res2[mask])  # /lamp[mask])
    p3 = ax.plot(wl[mask], x2[mask], alpha=0.5)  # /lamp[mask])
    res2 = signal.savgol_filter(x2, 71, 1)
    p4 = ax.plot(wl[mask], res2[mask])  # /lamp[mask])
    ax.set_zorder(ax2.get_zorder() + 1)  # put ax in front of ax2
    ax.patch.set_visible(False)  # hide the 'canvas'

    plt.savefig(savedir + "lockin_psd.png", dpi=300)
    plt.close()
