-- This reservoir simulation deck is made available under the Open Database
-- License: http://opendatacommons.org/licenses/odbl/1.0/. Any rights in
-- individual contents of the database are licensed under the Database Contents
-- License: http://opendatacommons.org/licenses/dbcl/1.0/

-- Copyright (C) 2015 Statoil

-- Norne full field model for SPE ATW 2013
RUNSPEC

DIMENS
${dic['nx']} ${dic['ny']} ${dic['nz']}   /

--NOSIM

GRIDOPTS
 'YES' 0 /

OIL

WATER

GAS

DISGAS

VAPOIL

ENDSCALE
NODIR   REVERS /

METRIC

SATOPTS
HYSTER  /

START
 06  'NOV' 1997 /

EQLDIMS
 5  100  20 /

EQLOPTS
 'THPRES'  /   no fine equilibration if swatinit is being used

REGDIMS
-- ntfip  nmfipr  nrfreg  ntfreg
    22      3      1*      20    /

TRACERS
--  oil  water  gas  env
    1*   7      1*    1*   /

WELLDIMS
 130  36  15  84 /

TABDIMS
--ntsfun ntpvt nssfun nppvt ntfip nrpvt ntendp
   ${2*int(max(dic['satnum_c']))}     2     33     60   16    60 /

-- WI_VFP_TABLES_080905.INC = 10-20
VFPIDIMS
 30    20   20 /

-- Table no.
-- DevNew.VFP        = 1
-- E1h.VFP           = 2
-- AlmostVertNew.VFP = 3
-- GasProd.VFP       = 4
-- NEW_D2_GAS_0.00003.VFP = 5
-- GAS_PD2.VFP = 6
-- pd2.VFP           = 8 (flowline south)
-- pe2.VFP           = 9 (flowline north)
-- PB1.PIPE.Ecl  = 31
-- PB2.PIPE.Ecl  = 32
-- PD1.PIPE.Ecl  = 33
-- PD2.PIPE.Ecl  = 34
-- PE1.PIPE.Ecl  = 35
-- PE2.PIPE.Ecl  = 36
-- B1BH.Ecl = 37
-- B2H.Ecl  = 38
-- B3H.Ecl  = 39
-- B4DH. Ecl= 40
-- D1CH.Ecl = 41
-- D2H.Ecl  = 42
-- D3BH.Ecl = 43

-- E1H.Ecl  = 45
-- E3CH.Ecl = 47
-- K3H.Ecl  = 48


VFPPDIMS
 19  10  10  10  0  50 /

FAULTDIM
10000 /

PIMTDIMS
1  51 /

NSTACK
 30 /

UNIFIN
UNIFOUT

--FMTOUT
--FMTIN

--OPTIONS
--77* 1 /

---------------------------------------------------------
--
--	Input of grid geometry
--
---------------------------------------------------------
GRID

NEWTRAN

-- Ask for an EGRID file; no .GRID output.
GRIDFILE
  0  1 /

-- optional for postprocessing of GRID
MAPAXES
 0.  100.  0.  0.  100.  0.  /

GRIDUNIT
METRES  /

-- requests output of INIT file
INIT

MESSAGES
 8*10000  20000 10000 1000 1* /

PINCH
 0.001 GAP  1* TOPBOT TOP/

NOECHO

--------------------------------------------------------
--
--  	Grid and faults
--
--------------------------------------------------------

-- Simulation grid, with slooping faults:
-- file in UTM coordinate system, for importing to DecisionSpace
INCLUDE
 '${dic['fol']}/preprocessing/NORNE_ATW2013_COARSER.GRDECL' /

 --
INCLUDE
 '${dic['fol']}/preprocessing/actnum.inc' /

-- Faults
INCLUDE
 '${dic['fol']}/preprocessing/fault.inc' /

-- Alteration of transmiscibility by use of the 'MULTFLT' keyword
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/FAULT/FAULTMULT_AUG-2006.INC' /

--------------------------------------------------------
--
--  	Input of grid parametres
--
--------------------------------------------------------

--
INCLUDE
 '${dic['fol']}/preprocessing/poro.inc' /

INCLUDE
 '${dic['fol']}/preprocessing/ntg.inc' /
 
INCLUDE
% if dic['rock'][0][1] > 0 and dic['study'] > 0:
'PERMX.inc' /
% else :
'${dic['fol']}/preprocessing/PERMX.inc' /
% endif

INCLUDE
% if dic['rock'][1][1] > 0 and dic['study'] > 0:
'PERMY.inc' /
% else :
'${dic['fol']}/preprocessing/PERMY.inc' /
% endif

INCLUDE
% if dic['rock'][2][1] > 0 and dic['study'] > 0:
'PERMZ.inc' /
% else :
'${dic['fol']}/preprocessing/PERMZ.inc' /
% endif

--------------------------------------------------------
--
--      Barriers
--
--------------------------------------------------------

-- MULTZ multiplies the transmissibility between blocks
-- (I, J, K) and (I, J, K+1), thus the barriers are at the
-- bottom of the given layer.

-- Region barriers
INCLUDE
 '${dic['fol']}/preprocessing/regionbarriers.inc' /

-- Field-wide barriers
EQUALS
  'MULTZ'    1.0      1  ${dic['nx']}  1 ${dic['ny']}  ${dic['k_f_c'][1]}    ${dic['k_f_c'][1]}  / Garn3       - Garn 2
  'MULTZ'    0.05     1  ${dic['nx']}  1 ${dic['ny']}  ${dic['k_f_c'][15]}   ${dic['k_f_c'][15]}  / Tofte 2.1.1 - Tofte 1.2.2
  'MULTZ'    0.001    1  ${dic['nx']}  1 ${dic['ny']}  ${dic['k_f_c'][18]}   ${dic['k_f_c'][18]}  / Tofte 1.1   - Tilje 4
  'MULTZ'    0.00001  1  ${dic['nx']}  1 ${dic['ny']}  ${dic['k_f_c'][20]}   ${dic['k_f_c'][20]}  / Tilje 3     - Tilje 2
-- The Top Tilje 2 barrier is included as MULTREGT = 0.0
/

-- Local barriers
INCLUDE
 '${dic['fol']}/preprocessing/localbarriers.inc' /

INCLUDE
 '${dic['fol']}/preprocessing/fluxnum.inc' /

-- modify transmissibilites between fluxnum using MULTREGT
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/PETRO/MULTREGT_D_27.prop' /

NOECHO

MINPV
  500 /

EDIT
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------

PROPS
--------------------------------------------------------------------------------
--
--    Input of fluid properties and relative permeability
--
---------------------------------------------------------

NOECHO

INCLUDE
'${dic['fol']}/preprocessing/INCLUDE/PVT/PVT-WET-GAS.INC' /

TRACER
SEA  WAT  /
HTO  WAT  /
S36  WAT  /
2FB  WAT  /
4FB  WAT  /
DFB  WAT  /
TFB  WAT  /
/

-- initial water saturation
--INCLUDE
--'INCLUDE/PETRO/SWINITIAL.INC' /

INCLUDE
 '${dic['fol']}/preprocessing/swatinit.inc' /

 INCLUDE
% if dic['deck'] == 0:
'${dic['fol']}/preprocessing/INCLUDE/RELPERM/SCAL_NORNE.INC' /
% elif dic['indc'] > 0:
'tables.inc' /
% else :
'${dic['fol']}/preprocessing/tables.inc' /
% endif
 
 SCALECRS
 YES /

-- endpoints may be used as tuning papameters
--EQUALS
--SWL 0.04 1 46 1 112 1  1   /
--SWL 0.05 1 46 1 112 2  2   /
--SWL 0.15 1 46 1 112 3  3   /
--SWL 0.15 1 46 1 112 4  4   /
--SWL 0.05 1 46 1 112 5  10  / Ile 2.2.2 and Ile 2.2.1, Ile 2.1.3, Ile 2.1.2, and Ile 2.1.1 Ile 1.3 and Ile 1.2
--SWL 0.16 1 46 1 112 11 12  / ile 1.1 and tofte 2.2
--SWL 0.07 1 46 1 112 13 15  / tofte 2.1
--SWL 0.06 1 46 1 112 16 16  / tofte 1.2.2
--SWL 0.12 1 46 1 112 17 22  / Tofte 1.2.1, Tofte 1.2.1, tofte 1.1, tilje
--/

--COPY
--  SWL SWCR /
--  SWL SGU  /
--/


--ADD
--SWCR   0.08  1 46 1 112 1 22  /
--/

-- SGU = 1 - SWL
--MULTIPLY
--SGU  -1  1 46 1 112 1 22  /
--/

--ADD
--SGU   1  1 46 1 112 1 22  /
--/

 -- Coarser endpoints.
INCLUDE
'${dic['fol']}/preprocessing/endpoints.inc' /

EQUALS
SGL   0.0  1 ${dic['nx']} 1 ${dic['ny']} 1 ${dic['nz']}  /
SGCR  0.03 1 ${dic['nx']} 1 ${dic['ny']} 1 ${dic['nz']}  /
SOWCR 0.13 1 ${dic['nx']} 1 ${dic['ny']} 1 ${dic['nz']}  /
SOGCR 0.07 1 ${dic['nx']} 1 ${dic['ny']} 1 ${dic['nz']}  /
SWU   1.0  1 ${dic['nx']} 1 ${dic['ny']} 1 ${dic['nz']}  /
/

-- Hysteresis input
EHYSTR
   0.1   0  0.1 1* KR /

COPY
 'SWCR'  'ISWCR'   1 ${dic['nx']} 1 ${dic['ny']}  ${dic['k_f_c'][5]} ${dic['nz']} /
 'SGU'   'ISGU'    1 ${dic['nx']} 1 ${dic['ny']}  ${dic['k_f_c'][5]} ${dic['nz']} /
 'SWL'   'ISWL'    1 ${dic['nx']} 1 ${dic['ny']}  ${dic['k_f_c'][5]} ${dic['nz']} /
 'SWU'   'ISWU'    1 ${dic['nx']} 1 ${dic['ny']}  ${dic['k_f_c'][5]} ${dic['nz']} /
 'SGL'   'ISGL'    1 ${dic['nx']} 1 ${dic['ny']}  ${dic['k_f_c'][5]} ${dic['nz']} /
 'SOGCR' 'ISOGCR'  1 ${dic['nx']} 1 ${dic['ny']}  ${dic['k_f_c'][5]} ${dic['nz']} /
 'SOWCR' 'ISOWCR'  1 ${dic['nx']} 1 ${dic['ny']}  ${dic['k_f_c'][5]} ${dic['nz']} /
 /

EQUALS
ISGCR 0.22 1 ${dic['nx']} 1 ${dic['ny']}  1  ${dic['nz']} /
/

RPTPROPS
1 1 1 5*0 0 /
--------------------------------------------------------------------------------


REGIONS

INCLUDE
 '${dic['fol']}/preprocessing/fipnum.inc' /
 
 INCLUDE
 '${dic['fol']}/preprocessing/satnum.inc' /

EQUALS
'PVTNUM'  1    1  ${dic['nx']}  1   ${dic['ny']}    1  ${dic['nz']}  /
/
--'SATNUM'  1    1  ${dic['nx']}  1   ${dic['ny']}    1  ${dic['nz']}  /
--'IMBNUM'  2    1  ${dic['nx']}  1   ${dic['ny']}    1  ${dic['nz']}  /

COPY
 'SATNUM' 'IMBNUM' /
/

ADD
 IMBNUM ${int(max(dic['satnum_c']))} 1  ${dic['nx']}  1   ${dic['ny']}    1  ${dic['nz']} /
/

INCLUDE
 '${dic['fol']}/preprocessing/eqlnum.inc' /

---------------------------------------------------------------------------------

SOLUTION

RPTRST
BASIC=2 KRO KRW KRG /

RPTSOL

FIP=3  SWAT /

---------------------------------------------------------------------------------
-- equilibrium data: do not include this file in case of RESTART

INCLUDE
'${dic['fol']}/preprocessing/INCLUDE/PETRO/E3.prop' /

THPRES
  1 2 0.588031 /
  2 1 0.588031 /
  1 3 0.787619 /
  3 1 0.787619 /
  1 4 7.00083  /
  4 1 7.00083  /
/

-- initialise injected tracers to zero
TVDPFSEA
1000   0.0
5000   0.0 /
TVDPFHTO
1000   0.0
5000   0.0 /
TVDPFS36
1000   0.0
5000   0.0 /
TVDPF2FB
1000   0.0
5000   0.0 /
TVDPF4FB
1000   0.0
5000   0.0 /
TVDPFDFB
1000   0.0
5000   0.0 /
TVDPFTFB
1000   0.0
5000   0.0 /

-------------------------------------------------------------------------------

SUMMARY

NEWTON
MLINEARS

--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/SUMMARY/summary.data' /

--
--INCLUDE
-- 'INCLUDE/SUMMARY/extra.inc' /

--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/SUMMARY/tracer.data' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/SUMMARY/gas.inc' /

--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/SUMMARY/wpave.inc' /

--------------------------------------------------------------------------------


SCHEDULE


DRSDT
 0  /

NOECHO

--------------------------------------------
--=======Production Wells========--
--------------------------------------------

--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/DevNew.VFP' /

--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/E1h.VFP' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/NEW_D2_GAS_0.00003.VFP' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/GAS_PD2.VFP' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/AlmostVertNew.VFP' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/GasProd.VFP' /


-- 01.01.07 new VFP curves for producing wells, matched with the latest well tests in Prosper. lmarr

--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/B1BH.Ecl' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/B2H.Ecl' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/B3H.Ecl' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/B4DH.Ecl' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/D1CH.Ecl' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/D2H.Ecl' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/D3BH.Ecl' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/E1H.Ecl' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/E3CH.Ecl' /
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/K3H.Ecl' /

--------------------------------------------
--=======Production Flowlines========--
--------------------------------------------
--
-- 16.5.02 new VFP curves for southgoing PD1,PD2,PB1,PB2 flowlines -> pd2.VFP
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/pd2.VFP' /
--
-- 16.5.02 new VFP curves for northgoing PE1,PE2 flowlines -> pe2.VFP
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/pe2.VFP' /


-- 24.11.06 new matched VLP curves for PB1 valid from 01.07.06
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/PB1.PIPE.Ecl' /

--24.11.06 new matched VLP curves for PB2 valid from 01.07.06
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/PB2.PIPE.Ecl' /

--24.11.06 new matched VLP curves for PD1 valid from 01.07.06
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/PD1.PIPE.Ecl' /

--24.11.06 new matched VLP curves for PD2 valid from 01.07.06
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/PD2.PIPE.Ecl' /

--24.11.06 new matched VLP curves for PE1 valid from 01.07.06
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/PE1.PIPE.Ecl' /

--24.11.06 new matched VLP curves for PE2 valid from 01.07.06
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/PE2.PIPE.Ecl' /


-------------------------------------------
--=======INJECTION FLOWLINES 08.09.2005     ========--
--------------------------------------------
-- VFPINJ nr. 10 Water injection flowline WIC
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/WIC.PIPE.Ecl' /

-- VFPINJ nr. 11 Water injection flowline WIF
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/WIF.PIPE.Ecl' /

--------------------------------------------
--=======   INJECTION Wells 08.09.2005       ========--
--------------------------------------------
-- VFPINJ nr. 12 Water injection wellbore Norne C-1H
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/C1H.Ecl' /

-- VFPINJ nr. 13 Water injection wellbore Norne C-2H
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/C2H.Ecl' /

-- VFPINJ nr. 14 Water injection wellbore Norne C-3H
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/C3H.Ecl' /

-- VFPINJ nr. 15 Water injection wellbore Norne C-4H
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/C4H.Ecl' /

-- VFPINJ nr. 16 Water injection wellbore Norne C-4AH
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/C4AH.Ecl' /

-- VFPINJ nr. 17 Water injection wellbore Norne F-1H
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/F1H.Ecl' /

-- VFPINJ nr. 18 Water injection wellbore Norne F-2H
--
INCLUDE
 '${dic['fol']}/preprocessing/INCLUDE/VFP/F2H.Ecl' /

-- VFPINJ nr. 19 Water injection wellbore Norne F-3 H
--
INCLUDE
'${dic['fol']}/preprocessing/INCLUDE/VFP/F3H.Ecl' /

-- VFPINJ nr. 20 Water injection wellbore Norne F-4H
--
INCLUDE
'${dic['fol']}/preprocessing/INCLUDE/VFP/F4H.Ecl' /

TUNING
1 10  0.1  0.15  3  0.3  0.3  1.20  /
5*   0.1   0.0001   0.02  0.02  /
2* 40 1* 15 /
/

-- only possible for ECL 2006.2+ version
ZIPPY2
'SIM=4.2' 'MINSTEP=1E-6' /

-- PI reduction in case of water cut
--INCLUDE
--'${dic['fol']}/preprocessing/INCLUDE/PI/pimultab_low-high_aug-2006.inc' /

-- History
INCLUDE
'${dic['fol']}/preprocessing/schedule.SCH' /
