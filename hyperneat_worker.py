import MySQLdb
mdb = MySQLdb.connect(...)
cur = mdb.cursor()


# Function keeps checking database for new encounters:

#PY#
while True:

    CloseRobots(distance, waittime, childtime)
    
    GetParents(endtime) #TODO Change for new code
    
	if parents == NULL:
		continue
    else:
        spawn_child()
	

################# FUNCTIONS ####################
	
    
def spawn_child()
#SH#
for ind in parents:

    run_hyperneat = Popen("gsub hn",cwd="./HyperNeat",stdin=subprocess.PIPE,stdout=subprocess.PIPE,shell=True)  # Double check this, may brick the whole thing
        run_hyperneat.STDIN("./"+str(exp_name)+"/"+str(firstID)+" ./"+str(exp_name)+"/"+str(secondID))
        	
        if (run_hyperneat.returncode != 0):
		    print run_hyperneat.returncode
			    run_hyperneat.kill()
        else:
            with io.open(pop_path, str(ChildID) + ".xml", 'w', encoding='utf-8') as f:
                f.write(str(run_hyperneat.STDOUT()))
                io.close()

