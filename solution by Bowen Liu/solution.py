#by Bowen Liu
from pyspark.sql import SQLContext
from pyspark.sql.types import *

sqlContext=SQLContext(sc)

#read input csv files and split them to columns based on comma
#read test_events.csv and test_impressions.csv when testing
lines1=sc.textFile("events.csv")
lines2=sc.textFile("impressions.csv")
parts1=lines1.map(lambda l: l.split(","))
parts2=lines2.map(lambda l: l.split(","))

#map them to their correct types
events=parts1.map(lambda p: (int(p[0]), p[1], int(p[2]), p[3], p[4]))
impressions=parts2.map(lambda p: (int(p[0]), int(p[1]), int(p[2]), p[3]))

#two strings below are the schemas
schemaString1="timestamp event_id advertiser_id user_id event_type"
schemaString2="timestamp advertiser_id creative_id user_id"

#specify the schemas
fields1=[StructField(field_name, StringType(), True) for field_name in schemaString1.split()]
fields2=[StructField(field_name, IntegerType(), True) for field_name in schemaString2.split()]

fields1[0].dataType=IntegerType()
fields1[2].dataType=IntegerType()

fields2[3].dataType=StringType()

schema1=StructType(fields1)
schema2=StructType(fields2)

#apply the schemas to the RDD
schemaEvents=sqlContext.createDataFrame(events, schema1)
schemaImpressions=sqlContext.createDataFrame(impressions, schema2)

#register the dataframe
schemaEvents.registerTempTable("events")
schemaImpressions.registerTempTable("impressions")

#dlist is a list to store the timestamp of duplicated events
dlist=list()

#this procedure below specifies the duplicated events and put them in the list
tempsql=sqlContext.sql("select timestamp, user_id, advertiser_id, event_type from events")
for tmp in tempsql.collect():
    if(tmp.timestamp not in dlist):
        duplicate=sqlContext.sql("select timestamp from events where timestamp-"+str(tmp.timestamp)+">0 and timestamp-"+str(tmp.timestamp)+"<60 and user_id='"+tmp.user_id+"' and advertiser_id="+str(tmp.advertiser_id)+" and event_type='"+tmp.event_type+"'")
        for s in duplicate.collect():
            dlist.append(s.timestamp)

#filter these duplicated events from the original table of events
newevents=sqlContext.sql("select * from events)
for a in dlist:
    r=newevents.filter(newevents.timestamp!=a)
    newevents=r

#register the new table
newevents.registerTempTable("newevents")

#this sql query displays the count of events happened after impressions group by the advertiser and event type
results1=sqlContext.sql("select newevents.advertiser_id,event_type,count(distinct event_id) as num from newevents,impressions where impressions.timestamp<newevents.timestamp and impressions.user_id=newevents.user_id and impressions.advertiser_id=newevents.advertiser_id group by newevents.advertiser_id,event_type")

#write the result to the output csv file, write test_count_of_events.csv when testing
results1.write.format("com.databricks.spark.csv").save("count_of_events.csv")

#this sql query displays the count of unique users group by the advertiser and event type
results2=sqlContext.sql("select newevents.advertiser_id,event_type,count(distinct newevents.user_id) as num from newevents,impressions where impressions.timestamp<newevents.timestamp and impressions.user_id=newevents.user_id and impressions.advertiser_id=newevents.advertiser_id group by newevents.advertiser_id,event_type")

#write the result to the output csv file, write test_count_of_users.csv when testing
results2.write.format("com.databricks.spark.csv").save("count_of_users.csv")

#use hdfs merge command to merge the output to a single csv file
#hdfs dfs -getmerge count_of_events.csv output/count_of_events.csv
#hdfs dfs -getmerge count_of_users.csv output/count_of_users.csv
