-- This reservoir simulation deck is made available under the Open Database
-- License: http://opendatacommons.org/licenses/odbl/1.0/. Any rights in
-- individual contents of the database are licensed under the Database Contents
-- License: http://opendatacommons.org/licenses/dbcl/1.0/

-- Copyright (C) 2022 Equinor

--==============================================================================
--		Synthetic reservoir simulation model Drogon (2020)
--==============================================================================

-- The Drogon model - the successor of the Reek model
-- Used in a FMU set up
-- Grid input data generated from RMS project 


-- =============================================================================
RUNSPEC
-- =============================================================================

-- Simulation run title
TITLE
 Drogon synthetic reservoir model

-- Simulation run start
START
 1 JAN 2018 /

-- Fluid phases present
OIL
GAS
WATER
DISGAS
VAPOIL

-- Measurement unit used
METRIC

DIMENS
${dic['nx']} ${dic['ny']} ${dic['nz']}   /

-- Options for equilibration
EQLOPTS
 'THPRES'  /

-- Dimensions and options for tracers
-- 2 water tracers
TRACERS
 1*  2 /

TABDIMS
-- NTSFUN  NTPVT  NSSFUN  NPPVT  NTFIP  NRPVT   
    ${round(dic['satnum_cmax'])}      2      200     24     6      20    /

-- Dimension of equilibration tables
INCLUDE
  '${dic['fol']}/preprocessing/include/runspec/drogon.eqldims' / -- exported by rms

-- Regions dimension data
INCLUDE
  '${dic['fol']}/preprocessing/include/runspec/drogon.regdims' / -- exported by rms

-- x-,y-,z- and multnum regions
INCLUDE
  '${dic['fol']}/preprocessing/include/runspec/drogon.gridopts' / -- exported by rms

-- Dimensions for fault data
FAULTDIM
 500 /

-- Well dimension data
-- nwmaxz: max wells in the model
-- ncwmax: max connections per well
-- ngmaxz: max groups in the model
-- nwgmax: max wells in any one group
WELLDIMS
-- nwmaxz  ncwmax  ngmaxz  nwgmax
   20       100     10       20 /

-- Dimensions for multi-segment wells
-- nswlmx: max multi-segment wells in the model
-- nsegmx: max segments per well
-- nlbrmx: max branches per multi-segment well
WSEGDIMS
-- nswlmx  nsegmx  nlbrmx
   3       150      100 /


-- Input and output files format
UNIFIN
UNIFOUT

-- Disables the initial index file output
NOINSPEC

-- Disables the restart index file output
NORSSPEC


-- print and stop limits
-- -----------print------------  -----------stop--------------------
-- mes  com  war  prb  err  bug  mes  com   war     prb    err  bug  
MESSAGES
   1*   1*   1*   1000 10   1*   1*    1*  1000000 7000    0   /


-- =============================================================================
GRID
-- =============================================================================
NOECHO

NEWTRAN

GRIDFILE
 0 1 /

INIT

--Generates connections across pinched-out layers
PINCH
 3*  ALL  /

MAPAXES
4.5606369E+05 5.9394410E+06 4.5606369E+05 5.9265510E+06 4.6748934E+05 5.9265510E+06 /

INCLUDE
 '${dic['fol']}/preprocessing/DROGON_COARSER.GRDECL' /

INCLUDE
 '${dic['fol']}/preprocessing/actnum.inc' /

INCLUDE
 '${dic['fol']}/preprocessing/fault.inc' / 

INCLUDE
 '${dic['fol']}/preprocessing/poro.inc' /

INCLUDE
 '${dic['fol']}/preprocessing/ntg.inc' /
 
INCLUDE
% if dic['rock'][0][1] > 0 and dic['mode'] in ["files","ert"]:
'permx.inc' /
% else :
'${dic['fol']}/preprocessing/permx.inc' /
% endif

INCLUDE
% if dic['rock'][1][1] > 0 and dic['mode'] in ["files","ert"]:
'permy.inc' /
% else :
'${dic['fol']}/preprocessing/permy.inc' /
% endif

INCLUDE
% if dic['rock'][2][1] > 0 and dic['mode'] in ["files","ert"]:
'permz.inc' /
% else :
'${dic['fol']}/preprocessing/permz.inc' /
% endif
 
INCLUDE
 '${dic['fol']}/preprocessing/multnum.inc' /

INCLUDE
 '${dic['fol']}/preprocessing/include/grid/drogon.multregt' / --from ert template

-- =============================================================================
EDIT
-- =============================================================================

INCLUDE
 '${dic['fol']}/preprocessing/trans.inc' /

-- =============================================================================
PROPS
-- =============================================================================

FILLEPS

INCLUDE
% if dic['deck'] == 0:                               
 '${dic['fol']}/preprocessing/include/props/drogon.sattab' / --exported by rms
% elif dic['indc'] > 0:
'tables.inc' /
% else :
'${dic['fol']}/preprocessing/tables.inc' /
% endif

INCLUDE
 '${dic['fol']}/preprocessing/swatinit.inc' /

INCLUDE
 '${dic['fol']}/preprocessing/include/props/drogon.pvt' /

-- Set up tracers
TRACER
 WT1  WAT 'g' /
 WT2  WAT 'g' /
/

EXTRAPMS
  4 /

-- =============================================================================
REGIONS
-- =============================================================================

INCLUDE
 '${dic['fol']}/preprocessing/eqlnum.inc' /

INCLUDE
 '${dic['fol']}/preprocessing/fipnum.inc' /

INCLUDE
 '${dic['fol']}/preprocessing/fipzon.inc' /

INCLUDE
 '${dic['fol']}/preprocessing/satnum.inc' /

INCLUDE
 '${dic['fol']}/preprocessing/pvtnum.inc' /


-- =============================================================================
SOLUTION
-- =============================================================================

% if dic['initial'] == 0:  
INCLUDE                                
 '${dic['fol']}/preprocessing/include/solution/drogon.equil' / --exported by rms   
INCLUDE
 '${dic['fol']}/preprocessing/include/solution/drogon.rxvd' / --!! manually created (7 equil regions)  
%else:
INCLUDE
 '${dic['fol']}/preprocessing/init.inc' / 
% endif

INCLUDE                                
 '${dic['fol']}/preprocessing/include/solution/drogon.thpres' / --exported by rms 
 
-- Initial tracer concentration vs depth for tracer WT1
TVDPFWT1
 1000  0.0 
 2500  0.0 /   

-- Initial tracer concentration vs depth for tracer WT2
TVDPFWT2
 1000  0.0 
 2500  0.0 /   

RPTSOL
 RESTART=2  FIP=2  'THPRES'  'FIPRESV' /

-- ALLPROPS --> fluid densities, viscosities , reciprocal formation volume factors and phase relative permeabilities
-- NORST=1  --> output for visualization only 
RPTRST
 ALLPROPS RVSAT RSSAT PBPD  NORST=1 RFIP RPORV /


-- =============================================================================
SUMMARY
-- =============================================================================

--RPTONLY

SUMTHIN
 1 /

INCLUDE
 '${dic['fol']}/preprocessing/include/summary/drogon.summary' /


-- =============================================================================
SCHEDULE
-- =============================================================================

INCLUDE
 '${dic['fol']}/preprocessing/schedule.SCH' / 

