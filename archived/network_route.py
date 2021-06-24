

#Create batch processing table with all catchment variable original data, catchment names, data type, statistics, watershed equivalent
#Import as panda df

#Aggregate all catchment attributes into one table
#Multiply all catchment attributes by catchment area
#Multiply water extent indicators by the extent of water so that it is weighted by water extent rather than by area.

#Routing
#For each river order
#if river_order > 1:
#Make panda dataset of all variables for [ORDER - 1]
#Make dictionary for all links of [ORDER -1]: HYRIV_ID : NEXT_DOWN
#Reverse dictionary so that it is, for ORDER: HYRIV_ID : NEXT_UP
#For each record, compute all statistics (SUM and AVERAGES and etc.)based on master table
#


#########################################################################################################################
##Make master table of catchment characteristics and calibrate for watershed accumulation
########################################################################################################################
arcpy.CopyRows_management(scatchpoly, 'master')
arcpy.DeleteField_management('master', ['Shape_Length','Shape_Area'])
arcpy.MakeTableView_management('master', 'masterview')
for tab in arcpy.ListTables():
    print(tab)
    if not tab=='master' or not tab=='masterdepthrock':
        try:
            if 'Value' in [f.name for f in arcpy.ListFields(tab)]:
                arcpy.AddJoin_management('masterview', 'GridID', tab, 'Value', join_type='KEEP_ALL')
            elif 'catchpoly188.GridID' in [f.name for f in arcpy.ListFields(tab)]:
                arcpy.AddJoin_management('masterview', 'GridID', tab, 'catchpoly188.GridID', join_type='KEEP_ALL')
            elif 'GRIDID' in [f.name for f in arcpy.ListFields(tab)]:
                arcpy.AddJoin_management('masterview', 'GridID', tab, 'GRIDID', join_type='KEEP_ALL')
        except:
            print('Could not join')
gdbname_ws = wd+'watershed_attri.gdb\\'
arcpy.CopyRows_management('masterview',gdbname_ws +'catchment_attributes') #CopyRows and TabletoTable after joining systematically crash.Not sure why. Do it in arcmap.
#In ArcMap, join all tables and take out useless fields (OBJECTID, etc.)
#Change <Null> values to 0 when relevant (road density, dam density, etc.)
attriformat = gdbname_ws +'catchment_attributes_format'
arcpy.CopyRows_management(gdbname_ws +'catchment_attributes', gdbname_ws +'catchment_attributes_format') #CopyRows and TabletoTable after joining systematically crash.Not syre why. Do it in arcmap.

#Multiply fields by catchment area so that can then be summed and divided by total watershed area so as to obtain area-weighted average for watershed
areaprodfields=['OBJECTID','CatArea','CatSolAvg','CatSloStd','CatSloAvg','CatPoroAvg','CatPETAvg','CatPermAvg','CatEroAvg','CatElvAvg','CatDRocAvg','CatBio01Av',
 'CatBio02Av','CatBio03Av','CatBio04Av','CatBio05Av','CatBio06Av','CatBio07Av','CatBio08Av','CatBio09Av','CatBio10Av','CatBio11Av','CatBio12Av','CatBio13Av',
 'CatBio14Av','CatBio15Av','CatBio16Av','CatBio17Av','CatBio18Av','CatBio19Av','CatAIAvg','CatPopDen','CatWatExt']
with arcpy.da.UpdateCursor(attriformat, areaprodfields) as cursor:
    for row in cursor:
        print(row[0])
        for f in range(2,len(areaprodfields)):
            if row[f]== None:
                print('pass')
            else:
                row[f]=row[f]*row[1]
                cursor.updateRow(row)
del row
del cursor

#Multiply pekel water extent indicators by the extent of water so that it is weighted by water extent rather than by area.
watareafields= ['OBJECTID','CatWatExt','CatWatSea','CatWatOcc','CatWatCha']
with arcpy.da.UpdateCursor(attriformat, watareafields) as cursor:
    for row in cursor:
        print(row[0])
        for f in range(2, len(watareafields)):
            if row[f]== None:
                print('pass')
            else:
                row[f]=row[f]*row[1]
                cursor.updateRow(row)
del row
del cursor

######################################################################################################################
#Route attributes to full watershed for each segment
#########################################################################################################################
#Join catchment attributes to drainage lines
arcpy.MakeFeatureLayer_management(sline,'slinelyr')
arcpy.AddJoin_management('slinelyr', 'GridID', attriformat, 'GridID', 'KEEP_ALL')
slineattri = outhydro+'streamnet118_attri'
arcpy.CopyFeatures_management('slinelyr',slineattri)

########################################################################################################################
# Compute watershed SUM statistics
########################################################################################################################
#Create template table #Do not reiterate if re-running code and no copy has been made of data
sumout_tab = gdbname_ws+ 'Ws_Attri_Sum'
scratch_tab = gdbname_ws+ 'scratch'
sumtabfields = sumfields + ['GridID']
arcpy.MakeFeatureLayer_management(outhydro+'linemidpoints_attri', 'spointlyrreduce',where_clause="ReaOrd>1") #Create another temporary layer as numpy array cannot hold the entire table (MemoryError: cannot allocate array memory)
array_sum =arcpy.da.FeatureClassToNumPyArray('spointlyrreduce', sumtabfields)
arcpy.da.NumPyArrayToTable(array_sum, scratch_tab)
arcpy.CreateTable_management(wd+'watershed_attri.gdb', 'Ws_Attri_Sum', scratch_tab)
arcpy.Delete_management(scratch_tab)
arcpy.Delete_management('spointlyrreduce')

#Create template table for appending data when cannot allocate memory to numpy array
memerror_tab = 'Ws_Attri_Sum_MemoryError'
arcpy.Statistics_analysis('spointlyr', memerror_tab, catstatslist)
arcpy.AddField_management(memerror_tab, field_name='GridID', field_type='LONG')
arcpy.CalculateField_management(memerror_tab,field='GridID', expression='999999')

nms= array_sum.dtype.names[:-1]
array_types = [(i,array_sum[i].dtype.kind) for i in nms if array_sum[i].dtype.kind in ('i', 'f')] + [('GridID','i')]

#Make subset of reaches to get data for
tz_bd = wd+'gadm1_lev0_Tanzania.shp'
arcpy.MakeFeatureLayer_management(outhydro+'linemidpoints_attri', 'spointlyr',where_clause="ReaOrd>1") ####### UPDATE #########
arcpy.SelectLayerByLocation_management('spointlyr', 'INTERSECT', tz_bd, selection_type='SUBSET_SELECTION')
arcpy.GetCount_management('spointlyr')
start = time.time()
x=0
by_col = numpy.empty([0, len(array_types)], dtype=array_types)
with arcpy.da.SearchCursor('spointlyr', ["GridID"]) as cursor:
    for row in cursor:
            #print(x)
            #x=x+1
            print(row[0])
            if row[0]==294478:
                #print(row[0])
                subcatch_id = row[0]
                expr = '"GridID" = %s' %subcatch_id
                arcpy.SelectLayerByAttribute_management('spointlyr', 'NEW_SELECTION', expr)
                arcpy.TraceGeometricNetwork_management(in_geometric_network= network, out_network_layer = "up_trace_lyr", in_flags = "spointlyr",
                                                       in_trace_task_type= "TRACE_UPSTREAM")
                up_tr = "up_trace_lyr\\lines"
                #print('Trace done!')
                try:
                    array=arcpy.da.FeatureClassToNumPyArray(up_tr, sumfields)
                    #print('Feature class to numpy array done!')
                    if len(by_col)==0:
                        by_col = numpy.array([tuple([array[i].sum() for i in nms if array[i].dtype.kind in ('i', 'f')]+[row[0]])],
                                              dtype=array_types)
                    elif len(by_col)>0 and len(by_col)<500:
                        by_col = numpy.concatenate((by_col,numpy.array([tuple([array[i].sum() for i in nms if array[i].dtype.kind in ('i', 'f')]+[row[0]])],dtype=array_types)),axis=0)
                    elif len(by_col)==500:
                        by_col = numpy.concatenate((by_col,numpy.array([tuple([array[i].sum() for i in nms if array[i].dtype.kind in ('i', 'f')]+[row[0]])],dtype=array_types)),axis=0)
                        scratch=arcpy.da.NumPyArrayToTable(by_col, scratch_tab)
                        #print('Numpy array to table done!')
                        arcpy.Append_management(scratch_tab, sumout_tab, "TEST")
                        #print('Append done!')
                        arcpy.Delete_management(scratch_tab)
                        by_col = numpy.empty([0, len(array_types)], dtype=array_types)
                except:
                    print('Error with numpy array method, use arcpy.Statistics_analysis')
                    inmemtab = r"in_memory/scratch"
                    arcpy.Statistics_analysis(up_tr, inmemtab, catstatslist)
                    print("stats analysis failed")
                    arcpy.AddField_management(inmemtab, field_name='GridID', field_type='LONG')
                    #with arcpy.da.UpdateCursor(inmemtab, ['GridID']) as cursormem:
                    #    for rowmem in cursormem:
                    #        rowmem[0]=row[0]
                    #        cursormem.updateRow(rowmem)
                    #del rowmem
                    #del cursormem
                    arcpy.CalculateField_management(inmemtab,field='GridID', expression=row[0])
                    arcpy.Append_management(inmemtab, memerror_tab, "TEST")
                    arcpy.Delete_management(inmemtab)
    scratch=arcpy.da.NumPyArrayToTable(by_col, scratch_tab)
    #print('Numpy array to table done!')
    arcpy.Append_management(scratch_tab, sumout_tab, "TEST")
arcpy.Delete_management(scratch_tab)
arcpy.Delete_management('spointlyr')
del row
del cursor
end = time.time()
print(end - start)

########################################################################################################################
# Compute watershed MAX statistics
#   Edit 2018/06/29: did not process these statistics for all of Tanzania. 10-day processing times. Future iterations could
#   merge this loop with the SUM statistics loop. In the end, compute watershed lake and reservoir index with quicker method
#   see L 912 and this loop would only be useful to compute WsElvMax, which is not used later on. So commented this section
#   out.
########################################################################################################################

#Create template table #Do not reiterate if re-running code and no copy has been made of data
# maxout_tab = gdbname_ws+ 'Ws_Attri_Max'
# scratch_tab = gdbname_ws+ 'scratch'
# maxfields = ['CatLakInd', 'CatResInd','CatElvMax'] #Create list of all fields to find max
# maxtabfields = maxfields + ['GridID']
# arcpy.MakeFeatureLayer_management(outhydro+'linemidpoints_attri', 'spointlyrreduce',where_clause="ReaOrd>3") #Create another temporary layer as numpy array cannot hold the entire table (MemoryError: cannot allocate array memory)
# array_max =arcpy.da.FeatureClassToNumPyArray('spointlyrreduce', maxtabfields)
# #arcpy.da.NumPyArrayToTable(array_max, scratch_tab)
# #arcpy.CreateTable_management(wd+'watershed_attri.gdb', 'Ws_Attri_Max', scratch_tab)
# arcpy.Delete_management(scratch_tab)
# arcpy.Delete_management('spointlyrreduce')
#
# nms= array_max.dtype.names[:-1]
# array_types = [(i,array_max[i].dtype.kind) for i in nms if array_max[i].dtype.kind in ('i', 'f')] + [('GridID','i')]
# arcpy.MakeFeatureLayer_management(outhydro+'linemidpoints_attri', 'spointlyr',where_clause="ReaOrd>1") ####### UPDATE #########
# arcpy.GetCount_management('spointlyr')
# start = time.time()
# x=0
# by_col = numpy.empty([0, len(array_types)], dtype=array_types)
# with arcpy.da.SearchCursor('spointlyr', ["GridID"]) as cursor:
#     for row in cursor:
#             print(x)
#             x=x+1
#             #if row[0]==450238:
#             #print(row[0])
#             subcatch_id = row[0]
#             expr = '"GridID" = %s' %subcatch_id
#             arcpy.SelectLayerByAttribute_management('spointlyr', 'NEW_SELECTION', expr)
#             arcpy.TraceGeometricNetwork_management(in_geometric_network= network, out_network_layer = "up_trace_lyr", in_flags = "spointlyr",
#                                                    in_trace_task_type= "TRACE_UPSTREAM")
#             up_tr = "up_trace_lyr\\lines"
#             #print('Trace done!')
#             array=arcpy.da.FeatureClassToNumPyArray(up_tr, maxfields)
#             #print('Feature class to numpy array done!')
#             if len(by_col)==0:
#                 by_col = numpy.array([tuple([array[i].max() for i in nms if array[i].dtype.kind in ('i', 'f')]+[row[0]])],
#                                       dtype=array_types)
#             elif len(by_col)>0 and len(by_col)<500:
#                 by_col = numpy.concatenate((by_col,numpy.array([tuple([array[i].max() for i in nms if array[i].dtype.kind in ('i', 'f')]+[row[0]])],dtype=array_types)),axis=0)
#             elif len(by_col)==500:
#                 by_col = numpy.concatenate((by_col,numpy.array([tuple([array[i].max() for i in nms if array[i].dtype.kind in ('i', 'f')]+[row[0]])],dtype=array_types)),axis=0)
#                 scratch=arcpy.da.NumPyArrayToTable(by_col, scratch_tab)
#                 #print('Numpy array to table done!')
#                 arcpy.Append_management(scratch_tab, maxout_tab, "TEST")
#                 #print('Append done!')
#                 arcpy.Delete_management(scratch_tab)
#                 by_col = numpy.empty([0, len(array_types)], dtype=array_types)
#     scratch=arcpy.da.NumPyArrayToTable(by_col, scratch_tab)
#     #print('Numpy array to table done!')
#     arcpy.Append_management(scratch_tab, maxout_tab, "TEST")
# arcpy.Delete_management(scratch_tab)
# arcpy.Delete_management('spointlyr')
# del row
# del cursor
# end = time.time()
# print(end - start)

########################################################################################################################

###################################################################################################################################################
#Make a copy of tables and merge tables with SUM statistics
arcpy.Copy_management(in_data=memerror_tab,out_data='Ws_Attri_Sum_MemoryError_20180531')
arcpy.Copy_management(in_data=sumout_tab,out_data=sumout_tab+'_20180531')
#Delete dummy first line in memerror_tab
with arcpy.da.UpdateCursor(memerror_tab, ['GridID']) as cursor:
    for row in cursor:
        if row[0] == 999999:
            cursor.deleteRow()
del row, cursor
#Edit field names and types for both tables to match
for fd in arcpy.ListFields(sumout_tab):
    if 'Cat' in fd.name: arcpy.AlterField_management(sumout_tab, fd.name, new_field_name=fd.name.replace('Cat','Ws'))
    if 'Cat' in fd.aliasName: arcpy.AlterField_management(sumout_tab, fd.name.replace('Cat','Ws'), new_field_alias=fd.aliasName.replace('Cat','Ws'))
tab1_fields=[f.name for f in arcpy.ListFields(sumout_tab)]
for fd in arcpy.ListFields(memerror_tab):
    if 'Cat' in fd.name or 'SUM_' in fd.name: arcpy.AlterField_management(memerror_tab, fd.name, new_field_name=fd.name.replace('Cat','Ws').replace('SUM_',''))
    if 'Cat' in fd.aliasName or 'SUM_' in fd.aliasName: arcpy.AlterField_management(memerror_tab, fd.name.replace('Cat','Ws').replace('SUM_',''), new_field_alias=fd.name.replace('Cat','Ws').replace('SUM_',''))
try:
    arcpy.DeleteField_management(memerror_tab,'FREQUENCY')
except Exception:
    e = sys.exc_info()[1]
    print(e.args[0])
#Modify 'WsMineden' field type
arcpy.AddField_management(sumout_tab, field_name='WsMineDen2', field_type=[f.type for f in arcpy.ListFields(memerror_tab) if f.name=='WsMineDen'][0])
arcpy.CalculateField_management(sumout_tab, field='WsMineDen2', expression='!WsMineDen!',expression_type="PYTHON")
arcpy.DeleteField_management(sumout_tab, 'WsMineDen')
arcpy.AlterField_management(sumout_tab, field='WsMineDen2', new_field_name='WsMineDen',new_field_alias='WsMineDen')
#Modify 'WsFlowAcc' field type
arcpy.AddField_management(sumout_tab, field_name='WsFlowAcc2', field_type=[f.type for f in arcpy.ListFields(memerror_tab) if f.name=='WsFlowAcc'][0] )
arcpy.CalculateField_management(sumout_tab, field='WsFlowAcc2', expression='!WsFlowAcc!',expression_type="PYTHON")
arcpy.DeleteField_management(sumout_tab, 'WsFlowAcc')
arcpy.AlterField_management(sumout_tab, field='WsFlowAcc2', new_field_name='WsFlowAcc',new_field_alias='WsFlowAcc')
#Check for differences among tables
comparetabs=arcpy.TableCompare_management(sumout_tab, memerror_tab, sort_field='GridID', compare_type='SCHEMA_ONLY',continue_compare='CONTINUE_COMPARE',
                                          out_compare_file=wd+'compare')
#Append tables
arcpy.Append_management(memerror_tab, sumout_tab, 'TEST')
arcpy.Delete_management(wd+'compare')
#Check for duplicates and keep the one with the maximum watershed area
arcpy.FindIdentical_management(sumout_tab,sumout_tab+'_identical',fields='GridID',output_record_option='ONLY_DUPLICATES')
dupliID = [id[0] for id in arcpy.da.SearchCursor(sumout_tab+'_identical', ['IN_FID'])]
duplicates = [[row[0],row[1],row[2]] for row in arcpy.da.SearchCursor(sumout_tab, ['OBJECTID','GridID','WsArea']) if row[0] in dupliID]
if len(duplicates)>0:
    d={}
    ldel=[]
    for sub in duplicates: #Inspired from https://stackoverflow.com/questions/34334381/removing-duplicates-from-a-list-of-lists-based-on-a-comparison-of-an-element-of
        k=sub[1]
        if k not in d:
            d[k]=sub
        elif sub[2] > d[k][2]:
            ldel.append(d[k][0])
            d[k]=sub
        else:
            #print(sub[0])
            ldel.append(sub[0])
expr= 'NOT "OBJECTID" IN ' + str(tuple(ldel))
arcpy.MakeTableView_management(sumout_tab, out_view='Ws_Attri_Sum_view', where_clause=expr)
arcpy.CopyRows_management('Ws_Attri_Sum_view','Ws_Attri_Sum_nodupli')
arcpy.Delete_management(sumout_tab+'_identical')
arcpy.Delete_management(wd+'compare')


###################################################
# Compute final variables for watersheds
watextdivlist = ['WsWatExt','WsWatOcc','WsWatcha','WsWatSea']
with arcpy.da.UpdateCursor(ws_tab,watextdivlist) as cursor:
    for row in cursor:
        if row[0]>0:
            for i in range(1,len(watextdivlist)): #Iterate over every selected field after area and divide it by water area
                row[i]=float(row[i])/float(row[0])
        cursor.updateRow(row)
del row
del cursor

areadivlist = [f.name for f in arcpy.ListFields(ws_tab) if not f.name in ['OBJECTID','WsWatOcc','WsWatcha','WsWatSea','WsLen_1','GridID',
                                                                          'WsRoadDen','WsDamDen','WsMineDen','WsLakInd', 'MaxLakAcc','WsResInd',
                                                                          'WsElvMax','Hylak_id']] #Keep area as first field and don't divide for dam, roads, mines, and PA density
with arcpy.da.UpdateCursor(ws_tab,areadivlist) as cursor:
    for row in cursor:
        for i in range(1,len(areadivlist)): #Iterate over every selected field after area and divide it by watershed area
            try:
                row[i]=float(row[i])/float(row[0])
            except:
                print('Error with field: '+areadivlist[i])
        cursor.updateRow(row)
del row
del cursor

#For land cover, direction, geology,and soil, compute percentage (for each row, dividing by sum over all fields) and identify field which is majority
for var in ['Dir','Geol','LC','Soil']:
    print(var)
    if 'Ws{}Maj'.format(var) not in [f.name for f in arcpy.ListFields(ws_tab)]:
        arcpy.AddField_management(in_table=ws_tab,field_name='Ws{}Maj'.format(var),field_type='TEXT')
    varfields = [f.name for f in arcpy.ListFields(ws_tab, '{}Sum*'.format(var))]
    varfields.insert(0, 'Ws{}Maj'.format(var))
    with arcpy.da.UpdateCursor(ws_tab, varfields) as cursor:
        for row in cursor:
            if row[1] is not None: denom=sum(row[1:]) #Sometimes geology was not computed for some watershed because of small boundaries of geology data
            for i in range(1,len(varfields)):
                if row[i] == max(row):
                    row[0]=str(varfields[i][len(var)+4:]) #Find the category ID that covers the most area in the watershed
                if row[i] is not None:
                    row[i]=row[i]/denom #Compute percentage area for each category
            cursor.updateRow(row)
    del cursor, row
#For forest loss, compute percentage and get rid of WsFLosSum_0 field
with arcpy.da.UpdateCursor(ws_tab, ['WsFLosSum_0','WsFLosSum_1']) as cursor:
    for row in cursor:
        if row[1] is not None:
            row[1]=row[1]/sum(row)
            cursor.updateRow(row)
    del cursor, row
arcpy.DeleteField_management(ws_tab,'WsFLosSum_0')


#For land cover, direction, geology,and soil, compute percentage (for each row, dividing by sum over all fields) and identify field which is majority
for var in ['Dir','Geol','LC','Soil']:
    arcpy.AddField_management(in_table=slinecat,field_name='Cat{}Maj'.format(var),field_type='TEXT')
    varfields = [f.name for f in arcpy.ListFields(slinecat, '{}Sum*'.format(var))]
    varfields.insert(0, 'Cat{}Maj'.format(var))
    with arcpy.da.UpdateCursor(slinecat, varfields) as cursor:
        for row in cursor:
            if row[1] is not None: denom=sum(row[1:]) #Sometimes geology was not computed for some watershed because of small boundaries of geology data
            for i in range(1,len(varfields)):
                if row[i] == max(row):
                    row[0]=str(varfields[i][len(var)+4:]) #Find the category ID that covers the most area in the watershed
                if row[i] is not None:
                    row[i]=row[i]/denom #Compute percentage area for each category
            cursor.updateRow(row)
    del row, cursor
#For forest loss, compute percentage and get rid of WsFLosSum_0 field
with arcpy.da.UpdateCursor(slinecat, ['CatFLosSum_0','CatFLosSum_1']) as cursor:
    for row in cursor:
        if row[1] is not None:
            row[1]=row[1]/sum(row)
        cursor.updateRow(row)
arcpy.DeleteField_management(slinecat, 'CatFLosSum_0')

##########################################################################################
# Fill in watershed attributes for streams of first order (i.e. append catchment attributes)
arcpy.MakeFeatureLayer_management(slinecat, 'slinecatlyr')
arcpy.SelectLayerByAttribute_management('slinecatlyr', 'NEW_SELECTION', 'ReaOrd=1')
order1=finalgdb +'catattri_order1'
arcpy.CopyRows_management('slinecatlyr',order1)

#Format catchment attribute table into Ws table
appfields=[f.name for f in arcpy.ListFields(order1) if f.name not in ['Shape_Length','CatFlowAcc','CatElvMin','CatCurvAvg']][9:]
appfields.insert(0,'OBJECTID')
appfields.append('GridID')
len(appfields)
len([f.name for f in arcpy.ListFields(ws_tab)])
arcpy.DeleteField_management(order1, [f.name for f in arcpy.ListFields(order1) if f.name not in appfields])
for fd in arcpy.ListFields(order1): #Edit field names and types for both tables to match
    if 'Cat' in fd.name: arcpy.AlterField_management(order1, fd.name, new_field_name=fd.name.replace('Cat','Ws'))
    if 'Cat' in fd.aliasName: arcpy.AlterField_management(order1, fd.name.replace('Cat','Ws'), new_field_alias=fd.aliasName.replace('Cat','Ws'))

arcpy.Merge_management(inputs=[ws_tab,order1],output=finalgdb+'wsattri_all')
arcpy.Delete_management(order1)

#Join watershed attributes
arcpy.MakeFeatureLayer_management(slinecat, 'slinecatlyr')
arcpy.AddJoin_management('slinecatlyr', 'GridID', finalgdb+'wsattri_all', 'GridID')
slinecatws = finalgdb +'streamnet118_catws'
arcpy.CopyFeatures_management('slinecatlyr', slinecatws)
arcpy.DeleteField_management(slinecatws, ['OBJECTID_1','GridID_1'])
[f.name for f in arcpy.ListFields(slinecatws)]

#Compute mines, dams, road, PA, and drainage densities for catchment and watershed
arcpy.AddField_management(slinecatws, 'CatDen', field_type='DOUBLE')
arcpy.AddField_management(slinecatws, 'WsDen', field_type='DOUBLE')
with arcpy.da.UpdateCursor(slinecatws, ['CatArea','CatLen_1','CatDen','CatRoadDen','CatDamDen','CatMineDen','CatPAPer']) as cursor:
    for row in cursor:
        row[2]=row[1]/row[0]
        row[3]=row[3]/row[0]
        row[4]=row[4]/row[0]
        row[5]=row[5]/row[0]
        cursor.updateRow(row)
    del row, cursor
with arcpy.da.UpdateCursor(slinecatws, ['WsArea','WsLen_1','WsDen','WsRoadDen','WsDamDen','WsMineDen','WsPAPer']) as cursor:
    for row in cursor:
        row[2]=row[1]/row[0]
        row[3]=row[3]/row[0]
        row[4]=row[4]/row[0]
        row[5]=row[5]/row[0]
        cursor.updateRow(row)
    del row, cursor

#Compute lake index
arcpy.MakeFeatureLayer_management(slinecatws, 'slinecatws_lyr')
arcpy.AddJoin_management('slinecatws_lyr', 'GridID', wslaktab, 'GridID')
slinecatws_index=gdbname_ws+'slinecatws_lakeindex'
arcpy.CopyFeatures_management('slinecatws_lyr',slinecatws_index)
arcpy.DeleteField_management(slinecatws_index, ['OBJECTID_1','GridID_1'])

[f.name for f in arcpy.ListFields(slinecatws_index)]
with arcpy.da.UpdateCursor(slinecatws_index, ['CatFlowAcc','WsLakInd','MaxLakAcc']) as cursor:
    for row in cursor:
        row[1]=float(row[2])/float(row[0])
        cursor.updateRow(row)
    del row, cursor
arcpy.CopyFeatures_management(slinecatws_index,slinecatws)
arcpy.Delete_management(slinecatws_index)
arcpy.DeleteField_management(slinecatws, 'WsResInd')
arcpy##########################################################################################
# Fill in watershed attributes for streams of first order (i.e. append catchment attributes)
arcpy.MakeFeatureLayer_management(slinecat, 'slinecatlyr')
arcpy.SelectLayerByAttribute_management('slinecatlyr', 'NEW_SELECTION', 'ReaOrd=1')
order1=finalgdb +'catattri_order1'
arcpy.CopyRows_management('slinecatlyr',order1)

#Format catchment attribute table into Ws table
appfields=[f.name for f in arcpy.ListFields(order1) if f.name not in ['Shape_Length','CatFlowAcc','CatElvMin','CatCurvAvg']][9:]
appfields.insert(0,'OBJECTID')
appfields.append('GridID')
len(appfields)
len([f.name for f in arcpy.ListFields(ws_tab)])
arcpy.DeleteField_management(order1, [f.name for f in arcpy.ListFields(order1) if f.name not in appfields])
for fd in arcpy.ListFields(order1): #Edit field names and types for both tables to match
    if 'Cat' in fd.name: arcpy.AlterField_management(order1, fd.name, new_field_name=fd.name.replace('Cat','Ws'))
    if 'Cat' in fd.aliasName: arcpy.AlterField_management(order1, fd.name.replace('Cat','Ws'), new_field_alias=fd.aliasName.replace('Cat','Ws'))

arcpy.Merge_management(inputs=[ws_tab,order1],output=finalgdb+'wsattri_all')
arcpy.Delete_management(order1)

#Join watershed attributes
arcpy.MakeFeatureLayer_management(slinecat, 'slinecatlyr')
arcpy.AddJoin_management('slinecatlyr', 'GridID', finalgdb+'wsattri_all', 'GridID')
slinecatws = finalgdb +'streamnet118_catws'
arcpy.CopyFeatures_management('slinecatlyr', slinecatws)
arcpy.DeleteField_management(slinecatws, ['OBJECTID_1','GridID_1'])
[f.name for f in arcpy.ListFields(slinecatws)]

#Compute mines, dams, road, PA, and drainage densities for catchment and watershed
arcpy.AddField_management(slinecatws, 'CatDen', field_type='DOUBLE')
arcpy.AddField_management(slinecatws, 'WsDen', field_type='DOUBLE')
with arcpy.da.UpdateCursor(slinecatws, ['CatArea','CatLen_1','CatDen','CatRoadDen','CatDamDen','CatMineDen','CatPAPer']) as cursor:
    for row in cursor:
        row[2]=row[1]/row[0]
        row[3]=row[3]/row[0]
        row[4]=row[4]/row[0]
        row[5]=row[5]/row[0]
        cursor.updateRow(row)
    del row, cursor
with arcpy.da.UpdateCursor(slinecatws, ['WsArea','WsLen_1','WsDen','WsRoadDen','WsDamDen','WsMineDen','WsPAPer']) as cursor:
    for row in cursor:
        row[2]=row[1]/row[0]
        row[3]=row[3]/row[0]
        row[4]=row[4]/row[0]
        row[5]=row[5]/row[0]
        cursor.updateRow(row)
    del row, cursor

#Compute lake index
arcpy.MakeFeatureLayer_management(slinecatws, 'slinecatws_lyr')
arcpy.AddJoin_management('slinecatws_lyr', 'GridID', wslaktab, 'GridID')
slinecatws_index=gdbname_ws+'slinecatws_lakeindex'
arcpy.CopyFeatures_management('slinecatws_lyr',slinecatws_index)
arcpy.DeleteField_management(slinecatws_index, ['OBJECTID_1','GridID_1'])

[f.name for f in arcpy.ListFields(slinecatws_index)]
with arcpy.da.UpdateCursor(slinecatws_index, ['CatFlowAcc','WsLakInd','MaxLakAcc']) as cursor:
    for row in cursor:
        row[1]=float(row[2])/float(row[0])
        cursor.updateRow(row)
    del row, cursor
arcpy.CopyFeatures_management(slinecatws_index,slinecatws)
arcpy.Delete_management(slinecatws_index)
arcpy.DeleteField_management(slinecatws, 'WsResInd')
arcpy.DeleteField_management(slinecatws, 'MaxLakAcc').DeleteField_management(slinecatws, 'MaxLakAcc')