# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0
#!/usr/bin/env python3

""""
Script to visualize the time series quantities
after the hm
"""

import os
import csv
import numpy as np
import warnings
from datetime import datetime
from resdata.summary import Summary
from resdata.grid import Grid
from resdata.resfile import ResdataFile
import matplotlib
import matplotlib.pyplot as plt
from datetime import timedelta

def visualizeData():
    """Visualize time series"""

    % if not dic["warnings"]:
    warnings.warn = lambda *args, **kwargs: None
    % endif
    output_folder = '${dic['fol']}'
    pycopm_path = '${dic['pat']}'
    num_satn = ${max(dic['satnum_c'])}
    num_para = ${len(dic["LET"])}
    name_para = [
    % for i in range(len(dic["LET"])):
    '${str(dic['LET'][i][0])}'${'\n' if loop.last else ','}\
    % endfor
    ]
    dist_para = [
    % for i in range(len(dic["LET"])):
    '${str(dic['LET'][i][3])} [${dic['LET'][i][4]}, ${dic['LET'][i][5]}]'${'\n' if loop.last else ','}\
    % endfor
    ]

    os.system(f"rm -rf {output_folder}/postprocessing")
    os.system(f"mkdir {output_folder}/postprocessing")
    os.system(f"mkdir {output_folder}/postprocessing/wells")
    os.system(f"mkdir {output_folder}/postprocessing/parameters")
    os.system(f"mkdir {output_folder}/postprocessing/saturation_functions")

    N = ${dic['net']}
    I = ${dic['Ni']}
    training=datetime.fromisoformat("${dic['date']}")

    wtab_sgof = [[],[]]
    wtab_swof = [[],[]]
    for ind, i in enumerate([0,I-1]):
        for r in range(N):
            ok_file = f"{output_folder}/output/simulations/realisation-{r}/iter-{i}/OK"
            if os.path.exists(ok_file) == 1:
                ini = ResdataFile(f'{output_folder}/output/simulations/realisation-{r}/iter-{i}/${dic['name']}_COARSER.INIT')
                tabdim = ini.iget_kw("TABDIMS")
                iswof = tabdim[0][20]
                nswe = tabdim[0][21]
                nsatnum = tabdim[0][22]
                isgof = tabdim[0][23]
                isgofn = tabdim[0][26] + 2*nswe*nsatnum + (nsatnum-1)*(2*nswe) + (2*nswe) + 2
                iswofn = tabdim[0][26] + 2*nswe*nsatnum
                table = np.array(ini.iget_kw("TAB"))
                tab_sgof = np.array(table[0][isgof-1:isgof+(3*nsatnum)*(nswe-1)+(3*nsatnum-1)])
                tab_swof = np.array(table[0][iswof-1:iswof+(3*nsatnum)*(nswe-1)+(3*nsatnum-1)])
                tab_sgof_kn = []
                tab_swof_kn = []
                for n in range(nsatnum):
                    avg_arr = np.mean(np.array(table[0][isgofn-1+2*n*nswe-2:isgofn+2*nswe-3+2*n*nswe]).reshape(-1,2), axis = 1)
                    avg_arr[0] = table[0][isgofn-1+2*n*nswe-2:isgofn+2*nswe-3+2*n*nswe][0]
                    avg_arr[-1] = table[0][isgofn-1+2*n*nswe-2:isgofn+2*nswe-3+2*n*nswe][-1]            
                    tab_sgof_kn.append(avg_arr)
                    avg_arr = np.mean(np.array(table[0][iswofn-1+2*n*nswe:iswofn+2*nswe-1+2*n*nswe]).reshape(-1,2), axis = 1)
                    avg_arr[0] = table[0][iswofn-1+2*n*nswe:iswofn+2*nswe-1+2*n*nswe][0]
                    avg_arr[-1] = table[0][iswofn-1+2*n*nswe:iswofn+2*nswe-1+2*n*nswe][-1]
                    tab_swof_kn.append(avg_arr)
                wtab_sgof[ind].append(np.append(tab_sgof, np.array(tab_sgof_kn).flatten()).reshape(4,nsatnum,nswe))
                wtab_swof[ind].append(np.append(tab_swof, np.array(tab_swof_kn).flatten()).reshape(4,nsatnum,nswe))
    
    if nsatnum < 100:
        colors = [[51 / 255.0, 153 / 255.0, 255 / 255.0],[0 / 255.0, 204 / 255.0, 0 / 255.0]]
        labels = ['Initial ensemble', 'Final ensemble']
        for n in range(nsatnum):
            figs, ax = plt.subplots()
            for i in range(min(I,2)):
                ax.plot(wtab_swof[i][0][0][n][wtab_swof[i][0][0][n]<1e19],wtab_swof[i][0][1][n][wtab_swof[i][0][0][n]<1e19], label=labels[i], color=colors[i])
                ax.plot(1.-wtab_swof[i][0][0][n][wtab_swof[i][0][0][n]<1e19],wtab_swof[i][0][3][n][wtab_swof[i][0][0][n]<1e19], color=colors[i])
                for r in range(len(wtab_swof[i])-1):
                    ax.plot(wtab_swof[i][r+1][0][n][wtab_swof[i][r+1][0][n]<1e19],wtab_swof[i][r+1][1][n][wtab_swof[i][r+1][0][n]<1e19], color=colors[i])
                    ax.plot(1.-wtab_swof[i][r+1][0][n][wtab_swof[i][r+1][0][n]<1e19],wtab_swof[i][r+1][3][n][wtab_swof[i][r+1][0][n]<1e19], color=colors[i])
            ax.set_title("SWOF")
            ax.legend()
            ax.set_xlabel("Water saturation [-]")
            ax.set_ylabel("Kr [-]")
            figs.savefig(f"postprocessing/saturation_functions/swof_kr_satnum_{n}.png", bbox_inches="tight")
            plt.close()
            figs, ax = plt.subplots()
            for i in range(2):
                ax.plot(wtab_swof[i][0][0][n][wtab_swof[i][0][0][n]<1e19],wtab_swof[i][0][2][n][wtab_swof[i][0][0][n]<1e19], label=labels[i], color=colors[i])
                for r in range(len(wtab_swof[i])-1):
                    ax.plot(wtab_swof[i][r+1][0][n][wtab_swof[i][r+1][0][n]<1e19],wtab_swof[i][r+1][2][n][wtab_swof[i][r+1][0][n]<1e19], color=colors[i])
            ax.set_title("SWOF")
            ax.legend()
            ax.set_xlabel("Water saturation [-]")
            ax.set_ylabel("Pc [Bar]")
            figs.savefig(f"postprocessing/saturation_functions/swof_pc_satnum_{n}.png", bbox_inches="tight")
            plt.close()
            figs, ax = plt.subplots()
            for i in range(2):
                ax.plot(wtab_sgof[i][0][0][n][wtab_sgof[i][0][0][n]<1e19],wtab_sgof[i][0][1][n][wtab_sgof[i][0][0][n]<1e19], label=labels[i], color=colors[i])
                ax.plot(1.-wtab_sgof[i][0][0][n][wtab_sgof[i][0][0][n]<1e19],wtab_sgof[i][0][3][n][wtab_sgof[i][0][0][n]<1e19], color=colors[i])
                for r in range(len(wtab_swof[i])-1):
                    ax.plot(wtab_sgof[i][r+1][0][n][wtab_sgof[i][r+1][0][n]<1e19],wtab_sgof[i][r+1][1][n][wtab_sgof[i][r+1][0][n]<1e19], color=colors[i])
                    ax.plot(1.-wtab_sgof[i][r+1][0][n][wtab_sgof[i][r+1][0][n]<1e19],wtab_sgof[i][r+1][3][n][wtab_sgof[i][r+1][0][n]<1e19], color=colors[i])
            ax.set_title("SGOF")
            ax.legend()
            ax.set_xlabel("Gas saturation [-]")
            ax.set_ylabel("Kr [-]")
            figs.savefig(f"postprocessing/saturation_functions/sgof_kr_satnum_{n}.png", bbox_inches="tight")
            plt.close()
            figs, ax = plt.subplots()
            for i in range(2):
                ax.plot(wtab_sgof[i][0][0][n][wtab_sgof[i][0][0][n]<1e19],wtab_sgof[i][0][2][n][wtab_sgof[i][0][0][n]<1e19], label=labels[i], color=colors[i])
                for r in range(len(wtab_swof[i])-1):
                    ax.plot(wtab_sgof[i][r+1][0][n][wtab_sgof[i][r+1][0][n]<1e19],wtab_sgof[i][r+1][2][n][wtab_sgof[i][r+1][0][n]<1e19], color=colors[i])
            ax.set_title("SGOF")
            ax.legend()
            ax.set_xlabel("Gas saturation [-]")
            ax.set_ylabel("Pc [Bar]")
            figs.savefig(f"postprocessing/saturation_functions/sgof_pc_satnum_{n}.png", bbox_inches="tight")
            plt.close()

    wells = {"WWPR" : []}
    wells["WOPR"] = []
    wells["WGPR"] = []
    var = {"WWPR" : ${dic['error'][0]}}
    var["WOPR"] = ${dic['error'][1]}
    var["WGPR"] = ${dic['error'][2]}
    minerr = {"WWPR" : ${dic['minerror'][0]}}
    minerr["WOPR"] = ${dic['minerror'][1]}
    minerr["WGPR"] = ${dic['minerror'][2]}
    cum = {"WWPR" : [[ ] for _ in range(I)]}
    cum["WOPR"] = [[ ] for _ in range(I)]
    cum["WGPR"] = [[ ] for _ in range(I)]
    fcum = {"FWPT" : [[ ] for _ in range(I)]}
    fcum["FOPT"] = [[ ] for _ in range(I)]
    fcum["FGPT"] = [[ ] for _ in range(I)]
    rcum = {"WWPR" : [ ]}
    rcum["WOPR"] = [ ]
    rcum["WGPR"] = [ ]
    rfcum = {"FWPT" : [ ]}
    rfcum["FOPT"] = [ ]
    rfcum["FGPT"] = [ ]
    fmass = {"FOPT" : [ ]}
    fmass["FGPT"] = [ ]
    fmass["FWPT"] = [ ]
    param = [[[[ ] for _ in range(num_satn)] for _ in range(num_para)] for _ in range(I)]

    figs = []
    axs = []
    FO = [[ ] for _ in range(N)]
    error_standard = 0
    error_ens = []
    error_hist = []
    time_ens = []
    for i in range(I):
        error_ens.append([0 for _ in range(N)])
        error_hist.append([])
        time_ens.append([])
    numCellsDefault = 0
    numCellsHm = 0
    grid = Grid(f"{pycopm_path}/reference_simulation/${dic['field']}/${dic['name']}.EGRID")
    for cell in grid.cells():
        if cell.active == 1:
            numCellsDefault += 1
    grid = Grid(f"{output_folder}/output/simulations/realisation-0/iter-0/${dic['name']}_COARSER.EGRID")
    for cell in grid.cells():
        if cell.active == 1:
            numCellsHm += 1
    smspecName = f"{pycopm_path}/reference_simulation/${dic['field']}/${dic['name']}.SMSPEC" 
    dbg = f"{pycopm_path}/reference_simulation/${dic['field']}/${dic['name']}.DBG"
    with open(dbg, "r", encoding="utf8") as file:
        sol = []
        for row in csv.reader(file, delimiter=":"):
            sol.append(row)
    time_standard = float(sol[-23][-1])
    smspec = Summary(smspecName)
    j = 0
    for type, ftype, dens in zip(["WWPR","WOPR","WGPR"],["FWPT","FOPT","FGPT"],[999.04100, 852.95669, 0.90358]):
        fmass[ftype] = dens*smspec[ftype+"H"].values[-1]
        for well in smspec.wells():
            if sum(smspec[type+"H:"+well].values)>0:
                wells[type].append(type+":"+well)
                j += 1
    linei = [[ ] for _ in range(j)]
    linef = [[ ] for _ in range(j)]
    meant = 0
    n_e = [0 for _ in range(I)]
    for i in range(len(smspec.dates)):
        if smspec.dates[i] > training:
            n_t = i
            break
    %if dic['field']=='drogon':
    n_t = 0
    %endif

    for type, ftype, dens in zip(["WWPR","WOPR","WGPR"],["FWPT","FOPT","FGPT"],[999.04100, 852.95669, 0.90358]):
        rfcum[ftype].append(dens*abs(smspec[ftype].values[-1]-smspec[ftype+"H"].values[-1]))
        rcum[type].append(0)
        for i in range(len(wells[type])):
            data = smspec[wells[type][i]]
            datah = smspec[wells[type][i][:4]+"H"+wells[type][i][4:]]
            for d_1, d_2 in zip(data.values[n_t:], datah.values[n_t:]):
                rcum[type][-1] += dens*abs(d_1-d_2)

    fig, ax = plt.subplots()
    j = 0
    k = 0
    for type in ["WOPR","WGPR","WWPR"]:
        for i in range(len(wells[type])):
            data = smspec[wells[type][i]]
            datah = smspec[wells[type][i][:4]+"H"+ wells[type][i][4:]]
            axs.append(ax)
            figs.append(fig)
            figs[j], axs[j] = plt.subplots()
            for d_1, d_2 in zip(data.values[n_t:], datah.values[n_t:]):
                error_standard += ((d_1-d_2)/max(minerr[type],var[type]*d_2))**2
                k += 1
            j += 1
    error_standard /= (2.*k)
    for r in range(N):
        if I > 1:
            ok_file = f"{output_folder}/output/simulations/realisation-{r}/iter-0/OK"
            if os.path.exists(ok_file) == 1:
                n_e[0] += 1
                smspecName = f"{output_folder}/output/simulations/realisation-{r}/iter-0/${dic['name']}_COARSER.SMSPEC"
                smspec = Summary(smspecName)
                for i in range(len(smspec.dates)):
                    if smspec.dates[i] > training:
                        n_t = i
                        break
                j = 0
                k = 0
                error_hist[0].append(0)
                for type, ftype, dens in zip(["WWPR","WOPR","WGPR"],["FWPT","FOPT","FGPT"],[999.04100, 852.95669, 0.90358]):
                    fcum[ftype][0].append(dens*abs(smspec[ftype].values[-1]-smspec[ftype+"H"].values[-1]))
                    cum[type][0].append(0)
                    for i in range(len(wells[type])):
                        data = smspec[wells[type][i]]
                        linei[j], = axs[j].plot(data.dates, data.values, color=[51 / 255.0, 153 / 255.0, 255 / 255.0])
                        datah = smspec[wells[type][i][:4]+"H"+wells[type][i][4:]]
                        for d_1, d_2 in zip(data.values[n_t:], datah.values[n_t:]):
                            error_ens[0][r] += ((d_1-d_2)/max(minerr[type],var[type]*d_2))**2
                            error_hist[0][-1] += ((d_1-d_2)/max(minerr[type],var[type]*d_2))**2
                            cum[type][0][-1] += dens*abs(d_1-d_2)
                            k += 1
                        j += 1
                error_ens[0][r] /= (2.*k)
                error_hist[0][-1] /= (2.*k)
                simTime = f"{output_folder}/output/simulations/realisation-{r}/iter-0/time_sim.txt"
                if N > 1:
                    file_para = f"{output_folder}/output/simulations/realisation-{r}/iter-0/parameters.txt"
                    data_param = np.genfromtxt(file_para, delimiter=" ")
                    if data_param.ndim == 1:
                        param[0][0].append(data_param[1])
                    else:
                        coun = 0
                        for i in range(num_para):
                            for n in range(num_satn):
                                param[0][i][n].append(data_param[coun, 1])
                                coun += 1
                try:
                    solData = []
                    for row in csv.reader(open(simTime), delimiter=" "):
                        solData.append(row)
                    time_ens[0].append(float(solData[0][-1]))
                except:
                    pass
            else:
                error_ens[0][r] += 1e10
        for ite in range(I-2):
            ok_file = f"{output_folder}/output/simulations/realisation-{r}/iter-{ite+1}/OK"
            if os.path.exists(ok_file) == 1:
                n_e[ite+1] += 1
                smspecName = f"{output_folder}/output/simulations/realisation-{r}/iter-{ite+1}/${dic['name']}_COARSER.SMSPEC"
                smspec = Summary(smspecName)
                for i in range(len(smspec.dates)):
                    if smspec.dates[i] > training:
                        n_t = i
                        break
                k = 0
                error_hist[ite+1].append(0)
                for type in ["WOPR","WGPR","WWPR"]:
                    for i in range(len(wells[type])):
                        data = smspec[wells[type][i]]
                        datah = smspec[wells[type][i][:4]+"H"+wells[type][i][4:]]
                        for d_1, d_2 in zip(data.values[n_t:], datah.values[n_t:]):
                            error_ens[ite+1][r] += ((d_1-d_2)/max(minerr[type],var[type]*d_2))**2
                            error_hist[ite+1][-1] += ((d_1-d_2)/max(minerr[type],var[type]*d_2))**2
                            k += 1
                error_ens[ite+1][r] /= (2.*k)
                error_hist[ite+1][-1] /= (2.*k)
                simTime = f"{output_folder}/output/simulations/realisation-{r}/iter-{ite+1}/time_sim.txt"
                try:
                    solData = []
                    for row in csv.reader(open(simTime), delimiter=" "):
                        solData.append(row)
                    time_ens[ite+1].append(float(solData[0][-1]))
                except:
                    pass
            else:
                error_ens[ite+1][r] += 1e10
        ok_file = f"{output_folder}/output/simulations/realisation-{r}/iter-{I-1}/OK"
        if os.path.exists(ok_file) == 1:
            n_e[I-1] += 1
            smspecName = f"{output_folder}/output/simulations/realisation-{r}/iter-{I-1}/${dic['name']}_COARSER.SMSPEC"
            smspec = Summary(smspecName)
            for i in range(len(smspec.dates)):
                if smspec.dates[i] > training:
                    n_t = i
                    break
            j = 0
            k = 0
            error_hist[-1].append(0)
            for type, ftype, dens in zip(["WWPR","WOPR","WGPR"],["FWPT","FOPT","FGPT"],[999.04100, 852.95669, 0.90358]):
                fcum[ftype][-1].append(dens*abs(smspec[ftype].values[-1]-smspec[ftype+"H"].values[-1]))
                cum[type][-1].append(0)
                for i in range(len(wells[type])):
                    data = smspec[wells[type][i]]
                    linef[j], = axs[j].plot(data.dates, data.values, color=[0 / 255.0, 204 / 255.0, 0 / 255.0])
                    datah = smspec[wells[type][i][:4]+"H"+wells[type][i][4:]]
                    for d_1, d_2 in zip(data.values[n_t:], datah.values[n_t:]):
                        error_ens[-1][r] += ((d_1-d_2)/max(minerr[type],var[type]*d_2))**2
                        error_hist[-1][-1] += ((d_1-d_2)/max(minerr[type],var[type]*d_2))**2
                        cum[type][-1][-1] += dens*abs(d_1-d_2)
                        k += 1
                    FO[r].append([data.dates,data.values])
                    j += 1
            error_ens[-1][r] /= (2.*k)
            error_hist[-1][-1] /= (2.*k)
            simTime = f"{output_folder}/output/simulations/realisation-{r}/iter-{I-1}/time_sim.txt"
            try:
                solData = []
                for row in csv.reader(open(simTime), delimiter=" "):
                    solData.append(row)
                time_ens[-1].append(float(solData[0][-1]))
                meant += float(solData[0][-1])
            except:
                pass
            if N > 1:
                file_para = f"{output_folder}/output/simulations/realisation-{r}/iter-{I-1}/parameters.txt"
                data_param = np.genfromtxt(file_para, delimiter=" ")
                if data_param.ndim == 1:
                    param[-1].append(data_param[1])
                else:
                    coun = 0
                    for i in range(num_para):
                        for n in range(num_satn):
                            param[-1][i][n].append(data_param[coun, 1])
                            coun += 1
        else:
            for type in ["WOPR","WGPR","WWPR"]:
                for i in range(len(wells[type])):
                    FO[r].append([data.dates,0*data.values])
                    error_ens[-1][r] += 1e10

    if n_e[I-1] > 0:
        meant /= n_e[I-1]
    eobs = []
    for i in range(I):
        eobs.append(np.where(np.array(error_ens[i])==min(error_ens[i])))
    paraName = f"{output_folder}/output/simulations/realisation-0/iter-0/parameters.txt"
    if os.path.exists(paraName) == 1:
        csvData = np.genfromtxt(paraName, delimiter=" ")
    else:
        csvData = []
    
    smspecName = f"{pycopm_path}/reference_simulation/${dic['field']}/${dic['name']}.SMSPEC" 
    smspec = Summary(smspecName)
    j = 0
    for type in ["WWPR","WOPR","WGPR"]:
        for i in range(len(wells[type])):
            if N > 1 and I == 1:
                linef[j].set_label('Ensemble')
                axs[j].plot(FO[eobs[0][0][0]][j][0], FO[eobs[0][0][0]][j][1], color=[255 / 255.0, 87 / 255.0, 51 / 255.0], lw=1.5 , label='Closest to all obs')
            elif I > 1:
                linei[j].set_label('Initial ensemble')
                linef[j].set_label('Final ensemble')
                axs[j].plot(FO[eobs[-1][0][0]][j][0], FO[eobs[-1][0][0]][j][1], color=[255 / 255.0, 87 / 255.0, 51 / 255.0], lw=1.5 , label='Closest to all obs')
                axs[j].axvline(x=training, color="black", ls="--", lw=1)
            else:
                linef[j].set_label('Single run')
            data = smspec[wells[type][i]]
            datah = smspec[wells[type][i][:4]+"H"+wells[type][i][4:]]
            axs[j].plot(data.dates, data.values, color='m', label = 'opm-tests')
            if sum(datah.values>0):
                axs[j].errorbar(datah.dates, datah.values, yerr= [max(minerr[type],var[type]*d_2) for d_2 in datah.values], color=[128 / 255.0, 128 / 255.0, 128 / 255.0], markersize='.5', elinewidth=.5, fmt='o', linestyle='', label = 'Data')
            axs[j].set_ylabel(f'{wells[type][i]} [SM3/day]', fontsize=12)
            axs[j].set_xlabel('Time [years]', fontsize=12)
            axs[j].xaxis.set_tick_params(size=6, rotation=45)
            axs[j].legend()
            axs[j].set_ylim(bottom=0)
            if sum(datah.values>0):
                figs[j].savefig(f"{output_folder}/postprocessing/wells/HISTO_DATA_{wells[type][i][:4]}_{wells[type][i][5:]}.png", bbox_inches="tight")
            else:
                figs[j].savefig(f"{output_folder}/postprocessing/wells/{wells[type][i][:4]}_{wells[type][i][5:]}.png", bbox_inches="tight")
            plt.close()
            j += 1
    if N == 1:
        os.system(f"cp -r {output_folder}/output/simulations/realisation-0/iter-0 {output_folder}/postprocessing")
        os.system(f"mv {output_folder}/postprocessing/iter-0 {output_folder}/postprocessing/closest_to_obs")
    else:
        os.system(f"cp -r {output_folder}/output/simulations/realisation-{eobs[-1][0][0]}/iter-{I-1} {output_folder}/postprocessing")
        os.system(f"mv {output_folder}/postprocessing/iter-{I-1} {output_folder}/postprocessing/closest_to_obs")
    %if len(dic['suffixes']) > 0:
    for i in range(I):
        for k in range(N):
            for suffix in [${dic['suffixes']}]:
                os.system(f"rm -rf {output_folder}/output/simulations/realisation-{k}/iter-{i}/*.{suffix}")
    %endif

    figs, ax = plt.subplots()
    ax.boxplot([error_hist[i] for i in range(I)], positions=[i for i in range(I)])
    ax.axhline(y=error_standard, color="black", ls="--", lw=1, label='opm-tests')
    ax.set_title(r"$O_{i,j}=\frac{1}{2N_{obs}}\sum_n^{N_{obs}}((d^{n}_{i,j}-d^{n})/\sigma_n)^2$")
    ax.legend()
    ax.set_xlabel("# iteration [-]")
    ax.set_ylabel("Missmatch [-]")
    ax.set_xticks(range(I))
    figs.savefig("postprocessing/dist_missmatch.png", bbox_inches="tight")
    figs, ax = plt.subplots()
    tab20s = matplotlib.colormaps['tab20']
    for i in range(I):
        ax.plot(i,sum(error_hist[i])/(len(error_hist[i])), markersize='10', marker='o', label=r"$N_{ens}=$"+f"{n_e[i]}", c=tab20s.colors[i])
    ax.axhline(y=error_standard, color="black", ls="--", lw=1, label=f'opm-tests (#Active cells:{numCellsDefault})')
    ax.set_title(r"$O_i=\frac{1}{N_{ens}}\sum_{j}^{N_{e}}O_{i,j}$, "+f"#HM parameters: {len(csvData)}, #Active cells: {numCellsHm}")
    ax.legend()
    ax.set_xlabel("# iteration [-]")
    ax.set_ylabel("Missmatch [-]")
    ax.set_xticks(range(I))
    figs.savefig("postprocessing/hm_missmatch.png", bbox_inches="tight")
    figs, ax = plt.subplots()
    ax.boxplot([time_ens[i] for i in range(I)], positions=[i for i in range(I)])
    ax.axhline(y=time_standard, color="black", ls="--", lw=1, label='opm-tests')
    ax.set_title(f"Total time of the HM: {timedelta(seconds=${'{0:.2f}'.format(time)})}")
    ax.set_xlabel("# iteration [-]")
    ax.set_xticks(range(I))
    ax.set_ylabel("Simulation time [s]")
    ax.legend()
    figs.savefig("postprocessing/solverTime.png", bbox_inches="tight")

    if N > 1 and num_satn < 100:
        for i, name in enumerate(name_para):
            figs, ax = plt.subplots()
            ax.boxplot([param[-1][i][n] for n in range(num_satn)], positions=[ii+1 for ii in range(num_satn)])
            ax.set_title(f"Initial distribution: {dist_para[i]}")
            ax.set_xlabel("# satnum [-]")
            ax.set_ylabel("Final distribution [-]")
            figs.savefig(f"postprocessing/parameters/final_parameter_distribution_{name}.png", bbox_inches="tight")
            plt.close()

    color=['b','g','r']
    names=["WWPR","WOPR","WGPR"]
    webvizr=[8.502e8, 3.606e8]
    for iter, webviz in zip([0,I-1], webvizr):  
        fig, ax = plt.subplots()
        allw = 0
        rallw = 0
        for type in names:
            allw += np.array(cum[type][iter])
            rallw += np.array(rcum[type])
        allw = np.array(allw)
        rallw = np.array(rallw)
        indc = np.argsort(allw)
        allw = np.sort(allw)
        ax.axhline(y=rallw.mean(), color="black", ls="--", lw=1, label=f'opm-tests: {rallw.mean():.3e}')
        % if dic['field']=='drogon':
        ax.axhline(y=webviz, color="black", ls=":", lw=1, marker="*", markevery=0.2, label=f'Mean (webviz): {webviz:.3e}')
        % endif
        ax.axhline(y=allw.mean(), color="black", ls="-", marker="o", markevery=0.2, lw=1, label=f'Mean (pycopm): {allw.mean():.3e}')
        ax.bar(range(len(allw)), allw, color=color[0], label=names[0])
        for i, type in enumerate(names[:-1]):
            allw -= np.array([cum[type][iter][r] for r in indc])
            ax.bar(range(len(allw)), allw, color=color[i+1], label=names[i+1])
        ax.set_title(f"Realization (iter-{iter})")
        ax.set_ylabel("Cumulative misfit")
        ax.legend()
        fig.savefig(f"{output_folder}/postprocessing/cumulative_misfit_rate_ite-{iter}.png", bbox_inches="tight")

    names=["FWPT","FOPT","FGPT"]
    webvizr=[1.914e9, 4.903e8]
    for iter, webviz in zip([0,I-1], webvizr): 
        fig, ax = plt.subplots()
        allw = 0
        rallw = 0
        for type in names:
            allw += np.array(fcum[type][iter])
            rallw += np.array(rfcum[type])
        allw = np.array(allw)
        rallw = np.array(rallw)
        indc = np.argsort(allw)
        allw = np.sort(allw)
        ax.axhline(y=rallw.mean(), color="black", ls="--", lw=1, label=f'opm-tests: {rallw.mean():.3e} kg')
        % if dic['field']=='drogon':
        ax.axhline(y=webviz, color="black", ls=":", lw=1, marker="*", markevery=0.2, label=f'Mean (webviz): {webviz:.3e} kg')
        % endif
        ax.axhline(y=allw.mean(), color="black", ls="-", marker="o", markevery=0.2, lw=1, label=f'Mean (pycopm): {allw.mean():.3e} kg')
        ax.bar(range(len(allw)), allw, color=color[0], label=names[0])
        for i, type in enumerate(names[:-1]):
            allw -= np.array([fcum[type][iter][r] for r in indc])
            ax.bar(range(len(allw)), allw, color=color[i+1], label=names[i+1])
        ax.set_title(f"Realization (iter-{iter})")
        ax.set_ylabel("Cumulative final mass")
        ax.legend()
        fig.savefig(f"{output_folder}/postprocessing/cumulative_misfit_mass_ite-{iter}.png", bbox_inches="tight")

    totalMass = 0
    webvizr=[19.06, 4.88]
    for name in names:
        totalMass += fmass[name]/100.
    for iter, webviz in zip([0,I-1], webvizr): 
        fig, ax = plt.subplots()
        allw = 0
        rallw = 0
        for type in names:
            allw += np.array(fcum[type][iter])/totalMass
            rallw += np.array(rfcum[type])/totalMass
        allw = np.array(allw)
        rallw = np.array(rallw)
        indc = np.argsort(allw)
        allw = np.sort(allw)
        goal = 4.88 - allw.mean()
        ax.axhline(y=rallw.mean(), color="black", ls="--", lw=1, label=f'opm-tests: {rallw.mean():.2f} %')
        % if dic['field']=='drogon':
        ax.axhline(y=webviz, color="black", ls=":", lw=1, marker="*", markevery=0.2, label=f'Mean (webviz): {webviz:.2f} %')
        % endif
        ax.axhline(y=allw.mean(), color="black", ls="-", marker="o", markevery=0.2, lw=1, label=f'Mean (pycopm): {allw.mean():.2f} %')
        ax.bar(range(len(allw)), allw, color=color[0], label=names[0]+f' ({fmass[names[0]]:.3e} kg)')
        for i, type in enumerate(names[:-1]):
            allw -= np.array([fcum[type][iter][r] for r in indc])/totalMass
            ax.bar(range(len(allw)), allw, color=color[i+1], label=names[i+1]+f' ({fmass[names[i+1]]:.3e} kg)')
        ax.set_title(f"Realization (iter-{iter})")
        ax.set_ylabel("Cumulative final mass [%]")
        ax.legend()
        fig.savefig(f"{output_folder}/postprocessing/cumulative_misfit_mass_normalized_ite-{iter}.png", bbox_inches="tight")

    print(f"\nThe postprocessing files have been written to {output_folder}/postprocessing")
    if N > 1:
        with open(f"{output_folder}/postprocessing/errors.txt", 'w') as f:
            f.write(f'Closest final realization to all obs:{eobs[-1][0][0]}\n')
            f.write(f'Number of parameters to HM: {len(csvData)}\n')
            f.write(f'Mean simulation time of a single ensemble : {timedelta(seconds=meant)}\n')
            f.write(f'Total execution time : {timedelta(seconds=${'{0:.2f}'.format(time)})}\n')
            f.write(f'Missmatch (standard simulation from opm-test deck): {error_standard : .4e}\n')
            for i in range(I):
                f.write(f'Iteration {i}; Number of ensembles {int(n_e[i])}\n')
                f.write(f'Missmatch (mean): {sum(error_hist[i])/(len(error_hist[i])) : .4e} \n')
                f.write(f'Missmatch (closest realization to all obs): {error_ens[i][eobs[i][0][0]]: .4e}\n')
        print(f'\nClosest final realization to all obs:{eobs[-1][0][0]}')
        print(f'Number of parameters to HM: {len(csvData)}')
        print(f'Mean simulation time of a single ensemble: {timedelta(seconds=meant)}')
        print(f'Total execution time: {timedelta(seconds=${'{0:.2f}'.format(time)})}')
        print(f'Missmatch (standard simulation from opm-test deck): {error_standard : .4e}')
        for i in range(I):
            print(f'Iteration {i}; Number of ensembles {int(n_e[i])}')
            print(f'Missmatch (mean): {sum(error_hist[i])/(len(error_hist[i])) : .4e}')
            print(f'Missmatch (closest realization to all obs): {error_ens[i][eobs[i][0][0]] : .4e}')
    else:
        with open(f"{output_folder}/postprocessing/errors.txt", 'w') as f:
            f.write(f'Missmatch (standard simulation from opm-test deck) : {error_standard : .4e}\n')
            f.write(f'Missmatch (single simulation): {error_ens[0][eobs[0][0][0]] : .4e}\n')
        print(f'\nMissmatch (standard simulation from opm-test deck): {error_standard : .4e}')
        print(f'Missmatch (single simulation): {error_ens[0][eobs[0][0][0]] : .4e}')
    % if dic['field']=='drogon':
    print(f'Difference (webviz - pycopm): {goal : .2f} (a positive number (percentage) is the goal)')
    print(f'See {output_folder}/postprocessing/cumulative_misfit_mass_normalized_ite-{iter}.png\n')
    if goal <= 0:
        print('To improve the goal, for example, you can try to run a hm study (mode = "ert") and increase the number ')
        print('of ensembles (mep), iterations (--weights), distribution type/intervals, random seed (rds).\n')
    % endif

if __name__ == "__main__":
    visualizeData()
