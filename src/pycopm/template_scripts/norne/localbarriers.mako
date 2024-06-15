-- This reservoir simulation deck is made available under the Open Database
-- License: http://opendatacommons.org/licenses/odbl/1.0/. Any rights in
-- individual contents of the database are licensed under the Database Contents
-- License: http://opendatacommons.org/licenses/dbcl/1.0/
  
-- Copyright (C) 2015 Statoil

-- Layer 8
EQUALS
--  'MULTZ'  0.005    ${dic['i_f_c'][6]} ${dic['i_f_c'][18]}  ${dic['j_f_c'][1]}  ${dic['j_f_c'][30]}  ${dic['k_f_c'][8]}  ${dic['k_f_c'][8]} /
'MULTZ'  0.02    ${dic['i_f_c'][6]} ${dic['i_f_c'][13]} ${dic['j_f_c'][30]}  ${dic['j_f_c'][50]} ${dic['k_f_c'][8]}  ${dic['k_f_c'][8]} /
/

-- MZ layer 10
EQUALS
  'MULTZ'   0.005  ${dic['i_f_c'][6]} ${dic['i_f_c'][14]}  ${dic['j_f_c'][11]}  ${dic['j_f_c'][18]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  C-3H
  'MULTZ'   0.03  ${dic['i_f_c'][14]} ${dic['i_f_c'][29]}  ${dic['j_f_c'][11]}  ${dic['j_f_c'][25]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  C south east
  'MULTZ'   0.05  ${dic['i_f_c'][14]} ${dic['i_f_c'][25]}  ${dic['j_f_c'][26]}  ${dic['j_f_c'][30]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  C-segm mid/B-2H
  'MULTZ'   0.25   ${dic['i_f_c'][6]} ${dic['i_f_c'][29]}  ${dic['j_f_c'][11]}  ${dic['j_f_c'][37]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  C-segm middle
  'MULTZ'   0.5   ${dic['i_f_c'][17]} ${dic['i_f_c'][17]}  ${dic['j_f_c'][42]}  ${dic['j_f_c'][54]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  C north west
  'MULTZ'   0.5    ${dic['i_f_c'][6]} ${dic['i_f_c'][12]}  ${dic['j_f_c'][38]}  ${dic['j_f_c'][39]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  C north west
  'MULTZ'   0.5    ${dic['i_f_c'][8]} ${dic['i_f_c'][12]}  ${dic['j_f_c'][40]}  ${dic['j_f_c'][40]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  C north west
  'MULTZ'   0.5   ${dic['i_f_c'][10]} ${dic['i_f_c'][12]}  ${dic['j_f_c'][41]}  ${dic['j_f_c'][43]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  C north west   
  'MULTZ'   0.5   ${dic['i_f_c'][18]} ${dic['i_f_c'][33]}  ${dic['j_f_c'][38]}  ${dic['j_f_c'][54]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  C1, D4 & D3
  'MULTZ'   0.5    ${dic['i_f_c'][6]} ${dic['i_f_c'][13]}  ${dic['j_f_c'][44]}  ${dic['j_f_c'][52]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  B-4AH
  'MULTZ'   0.01  ${dic['i_f_c'][13]} ${dic['i_f_c'][13]}  ${dic['j_f_c'][48]}  ${dic['j_f_c'][59]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  D-segm mid (B-4BH)
  'MULTZ'   0.01  ${dic['i_f_c'][14]} ${dic['i_f_c'][14]}  ${dic['j_f_c'][49]}  ${dic['j_f_c'][59]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  D-segm mid (B-4BH)
  'MULTZ'   0.01  ${dic['i_f_c'][15]} ${dic['i_f_c'][16]}  ${dic['j_f_c'][51]}  ${dic['j_f_c'][59]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  D-segm mid (B-4BH)
  'MULTZ'   0.05  ${dic['i_f_c'][17]} ${dic['i_f_c'][19]}  ${dic['j_f_c'][55]}  ${dic['j_f_c'][99]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  E1
  'MULTZ'   0.05  ${dic['i_f_c'][14]} ${dic['i_f_c'][14]}  ${dic['j_f_c'][60]}  ${dic['j_f_c'][62]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  E1
  'MULTZ'   0.05  ${dic['i_f_c'][15]} ${dic['i_f_c'][15]}  ${dic['j_f_c'][60]}  ${dic['j_f_c'][65]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  E1
  'MULTZ'   0.05  ${dic['i_f_c'][16]} ${dic['i_f_c'][16]}  ${dic['j_f_c'][60]}  ${dic['j_f_c'][69]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  E1 
  'MULTZ'   0.005  ${dic['i_f_c'][6]} ${dic['i_f_c'][9]}  ${dic['j_f_c'][52]}  ${dic['j_f_c'][60]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  F-3H/E-2H
  'MULTZ'   0.005  ${dic['i_f_c'][9]} ${dic['i_f_c'][9]}  ${dic['j_f_c'][53]}  ${dic['j_f_c'][57]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  F-3H/E-2H
  'MULTZ'   0.005 ${dic['i_f_c'][10]} ${dic['i_f_c'][10]}  ${dic['j_f_c'][54]}  ${dic['j_f_c'][58]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  F-3H/E-2H
  'MULTZ'   0.005 ${dic['i_f_c'][11]} ${dic['i_f_c'][11]}  ${dic['j_f_c'][55]}  ${dic['j_f_c'][58]}  ${dic['k_f_c'][10]}  ${dic['k_f_c'][10]}  /  F-3H/E-2H
/

-- MZ layer 15
EQUALS
  'MULTZ'   0.00003     ${dic['i_f_c'][6]} ${dic['i_f_c'][29]} ${dic['j_f_c'][11]} ${dic['j_f_c'][21]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} / C south
  'MULTZ'   0.00005   ${dic['i_f_c'][6]} ${dic['i_f_c'][29]}  ${dic['j_f_c'][22]} ${dic['j_f_c'][39]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /  C middle
  'MULTZ'   0.000001 ${dic['i_f_c'][19]} ${dic['i_f_c'][29]}  ${dic['j_f_c'][39]} ${dic['j_f_c'][49]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /  C-1H
  'MULTZ'   1.0      ${dic['i_f_c'][19]} ${dic['i_f_c'][29]}  ${dic['j_f_c'][38]} ${dic['j_f_c'][45]}  ${dic['k_f_c'][17]}  ${dic['k_f_c'][17]} /  C-1H
  'MULTZ'   0.005    ${dic['i_f_c'][16]} ${dic['i_f_c'][19]}  ${dic['j_f_c'][48]} ${dic['j_f_c'][61]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /  E-1H/D-3H
  'MULTZ'   0.0008    ${dic['i_f_c'][8]} ${dic['i_f_c'][18]}  ${dic['j_f_c'][40]} ${dic['j_f_c'][40]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /  C north
  'MULTZ'   0.0008    ${dic['i_f_c'][9]} ${dic['i_f_c'][18]}  ${dic['j_f_c'][41]} ${dic['j_f_c'][41]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /
  'MULTZ'   0.0008   ${dic['i_f_c'][10]} ${dic['i_f_c'][18]}  ${dic['j_f_c'][42]} ${dic['j_f_c'][43]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /
  'MULTZ'   0.0008   ${dic['i_f_c'][11]} ${dic['i_f_c'][18]}  ${dic['j_f_c'][44]} ${dic['j_f_c'][44]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /
  'MULTZ'   0.0008   ${dic['i_f_c'][12]} ${dic['i_f_c'][18]}  ${dic['j_f_c'][45]} ${dic['j_f_c'][45]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /
  'MULTZ'   0.0008   ${dic['i_f_c'][13]} ${dic['i_f_c'][18]}  ${dic['j_f_c'][46]} ${dic['j_f_c'][47]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /
  'MULTZ'   0.0008   ${dic['i_f_c'][14]} ${dic['i_f_c'][15]}  ${dic['j_f_c'][48]} ${dic['j_f_c'][48]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /
  'MULTZ'   0.0008   ${dic['i_f_c'][15]} ${dic['i_f_c'][15]}  ${dic['j_f_c'][49]} ${dic['j_f_c'][50]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /
  
  'MULTZ'   0.01      ${dic['i_f_c'][12]} ${dic['i_f_c'][12]} ${dic['j_f_c'][46]} ${dic['j_f_c'][56]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} / D-segm
  'MULTZ'   0.01      ${dic['i_f_c'][13]} ${dic['i_f_c'][13]} ${dic['j_f_c'][48]} ${dic['j_f_c'][59]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} / D-segm
  'MULTZ'   0.01      ${dic['i_f_c'][14]} ${dic['i_f_c'][14]} ${dic['j_f_c'][49]} ${dic['j_f_c'][62]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} / D-segm
  'MULTZ'   0.01      ${dic['i_f_c'][15]} ${dic['i_f_c'][15]} ${dic['j_f_c'][51]} ${dic['j_f_c'][65]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} / D-segm
  'MULTZ'   0.01      ${dic['i_f_c'][16]} ${dic['i_f_c'][19]} ${dic['j_f_c'][62]} ${dic['j_f_c'][69]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} / D-segm
  'MULTZ'   0.01      ${dic['i_f_c'][17]} ${dic['i_f_c'][19]} ${dic['j_f_c'][70]} ${dic['j_f_c'][99]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} / D-segm
   MULTZ    0.0035      ${dic['i_f_c'][6]}  ${dic['i_f_c'][7]} ${dic['j_f_c'][40]} ${dic['j_f_c'][60]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} / D, E west
   MULTZ    0.0035      ${dic['i_f_c'][8]}  ${dic['i_f_c'][8]} ${dic['j_f_c'][41]} ${dic['j_f_c'][60]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} /
   MULTZ    0.0035      ${dic['i_f_c'][9]}  ${dic['i_f_c'][9]} ${dic['j_f_c'][42]} ${dic['j_f_c'][52]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} /
   MULTZ    0.0035     ${dic['i_f_c'][10]}  ${dic['i_f_c'][10]} ${dic['j_f_c'][44]} ${dic['j_f_c'][49]} ${dic['k_f_c'][15]} ${dic['k_f_c'][15]} /
/

-- D-1H water
EQUALS
  'MULTZ'    1.0  ${dic['i_f_c'][22]}  ${dic['i_f_c'][24]}  ${dic['j_f_c'][21]}  ${dic['j_f_c'][22]}  ${dic['k_f_c'][11]}  ${dic['k_f_c'][11]} /  
  'MULTZ'    0.1  ${dic['i_f_c'][21]}  ${dic['i_f_c'][25]}  ${dic['j_f_c'][17]}  ${dic['j_f_c'][19]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /    
  'MULTZ'    1.0  ${dic['i_f_c'][22]}  ${dic['i_f_c'][24]}  ${dic['j_f_c'][17]}  ${dic['j_f_c'][19]}  ${dic['k_f_c'][17]}  ${dic['k_f_c'][17]} / 
  'MULTZ'    1.0  ${dic['i_f_c'][22]}  ${dic['i_f_c'][24]}  ${dic['j_f_c'][15]}  ${dic['j_f_c'][17]}  ${dic['k_f_c'][18]}  ${dic['k_f_c'][18]} /   
/  

-- B-1 & B-3 water
EQUALS
  'MULTZ'    0.1 ${dic['i_f_c'][12]}  ${dic['i_f_c'][13]}  ${dic['j_f_c'][34]}  ${dic['j_f_c'][35]}  ${dic['k_f_c'][15]}  ${dic['k_f_c'][15]} /  
/ 

-- RFT D_-H
EQUALS
  'MULTZ'  0.1     ${dic['i_f_c'][16]} ${dic['i_f_c'][19]} ${dic['j_f_c'][47]} ${dic['j_f_c'][53]} ${dic['k_f_c'][18]} ${dic['k_f_c'][18]} /  D-3H
/
