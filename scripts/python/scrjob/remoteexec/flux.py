import os
import re
from time import time

# flux imports
try:
    import flux
    from flux.job import JobspecV1
    from flux.resource import ResourceSet
    from flux.rpc import RPC
except:
    pass

from scrjob.remoteexec import RemoteExec, RemoteExecResult


class FLUX(RemoteExec):

    def __init__(self):
        # connect to the running Flux instance
        try:
            self.flux = flux.Flux()
        except:
            raise ImportError(
                'Error importing flux, ensure that the flux daemon is running.'
            )

        # when using flux labeled output, a rank and colon are prepended to each line
        # 23: hello, world
        self.re_labeled = re.compile('^(\d+): (.*)$')

    def rexec(self, argv, nodes, jobenv):
        result = RemoteExecResult(argv, nodes)

        nnodes, ntasks, ncores, argv = self.parsefluxargs(argv)

        ### Need to determine number of nodes to set nnodes and nntasks to N
        ### without specifying it is set above to just launch 1 task on 1 cpu on 1 node
        ### The size is the number of ranks flux start was launched with
        resp = RPC(self.flux, 'resource.status').get()
        rset = ResourceSet(resp['R'])
        nnodes = rset.nnodes
        ntasks = nnodes
        compute_jobreq = JobspecV1.from_command(command=argv,
                                                num_tasks=ntasks,
                                                num_nodes=nnodes,
                                                cores_per_task=ncores)

        ### create a yaml 'file' stream from a string to get JobspecV1.from_yaml_stream()
        #   This may allow to explicitly specify the nodes to run on
        # string = 'yaml spec'
        # stream = io.StringIO(string)
        # compute_jobreq = JobspecV1.from_yaml_stream(stream)
        compute_jobreq.cwd = os.getcwd()
        compute_jobreq.environment = dict(os.environ)
        compute_jobreq.setattr_shell_option("output.stdout.label", True)
        compute_jobreq.setattr_shell_option("output.stderr.label", True)
        prefix = jobenv.dir_scr()
        timestamp = str(time())

        # time will return posix timestamp like -> '1628179160.1724932'
        # some unique filename to send stdout/stderr to
        ### the script prepends the rank to stdout, not stderr.
        outfile = os.path.join(prefix, 'out' + timestamp)
        errfile = os.path.join(prefix, 'err' + timestamp)

        # all tasks will write their stdout to this file
        compute_jobreq.stdout = outfile
        compute_jobreq.stderr = errfile
        job = flux.job.submit(self.flux, compute_jobreq, waitable=True)

        # get the hostlist to swap ranks for hosts
        nodelist = rset.nodelist
        future = flux.job.wait_async(self.flux, job)
        status = future.get_status()

        # TODO: can we set result.set_rc(node, rc) for each process?

        # don't fail if can't open a file, just leave output blank
        try:
            with open(outfile, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    m = self.re_labeled.match(line)
                    if m:
                        rank = int(m.groups(0)[0])
                        node = nodelist[rank]
                        val = m.groups(0)[1]
                        result.append_stdout(node, val)
        except:
            pass

        try:
            with open(errfile, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    m = self.re_labeled.match(line)
                    if m:
                        rank = int(m.groups(0)[0])
                        node = nodelist[rank]
                        val = m.groups(0)[1]
                        result.append_stderr(node, val)
        except:
            pass

        try:
            os.remove(outfile)
        except:
            pass

        try:
            os.remove(errfile)
        except:
            pass

        return result
