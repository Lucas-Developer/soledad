import base64
import functools
import numpy
import os
import psutil
import pytest
import random
import threading
import time

from twisted.internet import threads, reactor


# we have to manually setup the events server in order to be able to signal
# events. This is usually done by the enclosing application using soledad
# client (i.e. bitmask client).
from leap.common.events import server
server.ensure_server()


#
# pytest customizations
#

def pytest_addoption(parser):
    parser.addoption(
        "--watch-resources", default=False, action="store_true",
        help="whether to monitor CPU and memory percentages during test run. "
             "**Warning**: enabling this will impact the time taken by the "
             "benchmarked code, so use with caution!")


# mark benchmark tests using their group names (thanks ionelmc! :)
def pytest_collection_modifyitems(items):
    for item in items:
        bench = item.get_marker("benchmark")
        if bench and bench.kwargs.get('group'):
            group = bench.kwargs['group']
            marker = getattr(pytest.mark, 'benchmark_' + group)
            item.add_marker(marker)


#
# benchmark fixtures
#

@pytest.fixture()
def payload():
    def generate(size):
        random.seed(1337)  # same seed to avoid different bench results
        payload_bytes = bytearray(random.getrandbits(8) for _ in xrange(size))
        # encode as base64 to avoid ascii encode/decode errors
        return base64.b64encode(payload_bytes)[:size]  # remove b64 overhead
    return generate


@pytest.fixture()
def txbenchmark(monitored_benchmark):
    def blockOnThread(*args, **kwargs):
        return threads.deferToThread(
            monitored_benchmark, threads.blockingCallFromThread,
            reactor, *args, **kwargs)
    return blockOnThread


@pytest.fixture()
def txbenchmark_with_setup(monitored_benchmark_with_setup):
    def blockOnThreadWithSetup(setup, f):
        def blocking_runner(*args, **kwargs):
            return threads.blockingCallFromThread(reactor, f, *args, **kwargs)

        def blocking_setup():
            args = threads.blockingCallFromThread(reactor, setup)
            try:
                return tuple(arg for arg in args), {}
            except TypeError:
                    return ((args,), {}) if args else None

        def bench():
            return monitored_benchmark_with_setup(
                blocking_runner, setup=blocking_setup,
                rounds=4, warmup_rounds=1)
        return threads.deferToThread(bench)
    return blockOnThreadWithSetup


#
# resource monitoring
#

class ResourceWatcher(threading.Thread):

    sampling_interval = 0.1

    def __init__(self):
        threading.Thread.__init__(self)
        self.process = psutil.Process(os.getpid())
        self.running = False
        # monitored resources
        self.cpu_percent = None
        self.memory_samples = []
        self.memory_percent = None

    def run(self):
        self.running = True
        self.process.cpu_percent()
        while self.running:
            sample = self.process.memory_percent(memtype='rss')
            self.memory_samples.append(sample)
            time.sleep(self.sampling_interval)

    def stop(self):
        self.running = False
        self.join()
        # save cpu usage info
        self.cpu_percent = self.process.cpu_percent()
        # save memory usage info
        memory_percent = {
            'sampling_interval': self.sampling_interval,
            'samples': self.memory_samples,
            'stats': {},
        }
        for stat in 'max', 'min', 'mean', 'std':
            fun = getattr(numpy, stat)
            memory_percent['stats'][stat] = fun(self.memory_samples)
        self.memory_percent = memory_percent


def _monitored_benchmark(benchmark_fixture, benchmark_function,
                         *args, **kwargs):
    # setup resource monitoring
    watcher = ResourceWatcher()
    watcher.start()
    # run benchmarking function
    benchmark_function(*args, **kwargs)
    # store results
    watcher.stop()
    benchmark_fixture.extra_info.update({
        'cpu_percent': watcher.cpu_percent,
        'memory_percent': watcher.memory_percent,
    })


def _watch_resources(request):
    return request.config.getoption('--watch-resources')


@pytest.fixture
def monitored_benchmark(benchmark, request):
    if not _watch_resources(request):
        return benchmark
    return functools.partial(
        _monitored_benchmark, benchmark, benchmark)


@pytest.fixture
def monitored_benchmark_with_setup(benchmark, request):
    if not _watch_resources(request):
        return benchmark.pedantic
    return functools.partial(
        _monitored_benchmark, benchmark, benchmark.pedantic)
