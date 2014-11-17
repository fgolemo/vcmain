# Python main script
import random
from subprocess import Popen
import os.path, time, glob, shutil, mysql.connector, ConfigParser
import subprocess
import sys
import signal

# import workers
from db import DB
import hyperneat_worker as hn
import voxelyze_worker as vox
import postprocessing_worker as pp


class EC14controller():
    base_path = ""
    db = None
    pause_time = 10
    time_start = time.time()
    timer = 0
    wall_time = 290
    run = 0
    dbString = ""
    dbParams = ""
    exp_name = ""
    hnWorker = None
    voxWorker = None
    ppWorker = None
    newExperiment = False
    pop_size = 0
    pop_random = 0
    pop_random_start_end = (0, 0)
    indiv_max_age = 0
    arena_x = 0
    arena_y = 0
    arena_type = ""
    config = None
    path_prefix = "~/EC14-Exp-"

    random_granularity = 10000.0

    yes = {'yes', 'y', 'ye'}
    no = {'no', 'n', ''}

    def __init__(self):
        self.config = ConfigParser.RawConfigParser()

    def installFiles(self):
        """ Copy script files into experiment directory and saves config
        :return: None
        """

        os.makedirs(self.base_path)
        os.makedirs(self.base_path + "scripts/")
        os.makedirs(self.base_path + "config/")
        os.makedirs(self.base_path + "population/")
        os.makedirs(self.base_path + "traces_duringVox/")
        os.makedirs(self.base_path + "traces_afterVox/")
        os.makedirs(self.base_path + "pool/")
        os.makedirs(self.base_path + "logs/")

        shutil.copy(self.configPath, self.base_path + "config/config.ini")

        files = glob.iglob("./*.py")
        for f in files:
            if os.path.isfile(f):
                shutil.copy(f, self.base_path + "scripts/")

    def getDB(self):
        """ retrieve database string from config or cache
        :return: None
        """

        self.db = DB(self.dbString, self.exp_name, self.end_time, self.indiv_max_age)
        self.dbParams = (self.dbString, self.exp_name, self.end_time, self.indiv_max_age)

    def createPopulaton(self):
        """ creates the initial population in the database
        :return: None
        """

        for i in range(self.pop_size):
            birth = 0
            if (self.pop_random):
                birth = (random.randrange(self.pop_random_start * self.random_granularity,
                                          self.pop_random_end * self.random_granularity)
                         / self.random_granularity)
            x = random.randrange(0, self.arena_x * self.random_granularity) / self.random_granularity
            y = random.randrange(0, self.arena_y * self.random_granularity) / self.random_granularity
            self.db.createIndividual(birth, x, y)

    def readConfig(self, filename):
        self.config.read(filename)
        self.dbString = self.config.get('DB', 'db_string')

        self.exp_name = self.config.get('Experiment', 'name')
        self.path_prefix = self.config.get('Experiment', 'path_prefix')
        self.debug = self.config.getboolean('Experiment', 'debug')
        self.wall_time = self.config.getint('Experiment', 'self_wall_time')
        self.end_time = self.config.getfloat('Experiment', 'end_time')
        self.random_granularity = self.config.getfloat('Experiment', 'random_granularity')

        self.arena_y = self.config.getfloat('Arena', 'x')
        self.arena_x = self.config.getfloat('Arena', 'y')
        self.arena_type = self.config.get('Arena', 'type')

        self.pop_size = self.config.getint('Population', 'size')
        self.pop_random = self.config.getboolean('Population', 'random')
        self.pop_random_start = self.config.getfloat('Population', 'random_start')
        self.pop_random_end = self.config.getfloat('Population', 'random_end')

        self.pause_time = self.config.getint('Workers', 'pause_time')

    def isNewExperiment(self):
        self.base_path = os.path.expanduser(self.path_prefix + self.exp_name) + "/"
        print(self.base_path)
        if not os.path.isdir(self.base_path):
            return True
        return False

    def initialize(self):
        self.readConfig(self.configPath)
        self.getDB()
        if (self.isNewExperiment()):
            self.installFiles()
            self.db.dropTables()
            self.db.createTables()
            self.createPopulaton()

    def launchWorkers(self):
        # launch workers
        self.hnWorker = hn.HNWorker(self.dbParams, self.configPath)
        self.hnWorker.start()
        self.voxWorker = vox.VoxWorker(self.dbParams, self.configPath)
        self.voxWorker.start()
        self.ppWorker = pp.PostprocessingWorker(self.dbParams, self.configPath)
        self.ppWorker.start()

    def handleParams(self):
        if len(sys.argv) > 3:
            print(
                "I take a maximum of 2 arguments: first the relative path to the config file, then [optional] the number of the resubmit... quitting.")
            quit()

        if len(sys.argv) == 3:
            self.run = int(sys.argv[2])

        if len(sys.argv) > 1:
            self.configPath = sys.argv[1]
        else:
            self.configPath = "./config.ini"

        self.configPath = os.path.abspath(self.configPath)
        print("using config file: " + self.configPath)

    def start(self):
        self.handleParams()
        self.initialize()
        self.launchWorkers()

        signal.signal(signal.SIGINT, self.keyboard_exit)

        while (time.time() - self.time_start <= self.wall_time - self.pause_time):
            unfinished = self.db.getUnfinishedIndividuals()
            if unfinished == 0:
                print("nothing left to do, quiting")
                self.clean_exit()
            time.sleep(self.pause_time)

        self.resubmit()

    def resubmit(self):
        logPrefix = "main.run{n}".format(n=self.run + 1)
        logPath = self.base_path + "logs/" + logPrefix
        cwd = os.path.dirname(os.path.realpath(__file__))

        cmd = "qsub -o {logpath}.output.log -e {logpath}.error.log -l walltime={walltime} -v "+\
              "config={config},run={run},cwd={cwd} {cwd}/scripts/main-resub.sh"

        qsub = subprocess.check_output(cmd.format(logpath=logPath,
                                                  walltime=self.wall_time,
                                                  config=self.configPath,
                                                  run=self.run + 1,
                                                  cwd=cwd),
                                       shell=True)
        print("MAIN: resubmitted myself as:" + str(qsub) )

    def keyboard_exit(self, signal, frame):
        print("\n-------------\nreceived CTRL+C... exiting gracefully.\n-------------\n")
        self.clean_exit()

    def clean_exit(self):
        self.hnWorker.join()
        self.voxWorker.join()
        self.ppWorker.join()
        sys.exit(0)


ctrl = EC14controller()
ctrl.start()
