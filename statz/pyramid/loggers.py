import resource

class Logger(object):
    pass

class MemoryLogger(Logger):
    def handle_request(self, event, call_stats):
        """
        Intercepts a new request creation and defines single request data
        used to metric memory
        """
        call_stats["start_rusage"] = resource.getrusage(resource.RUSAGE_SELF)

    def handle_response(self, event, call_stats):
        """
        Intercepts a new request creation and defines single request data
        used to metric memory
        """
        mem = resource.getrusage(
            resource.RUSAGE_SELF
        )
        start_mem = call_stats.pop("start_rusage", None)
        if start_mem is not None:
            mem_delta = mem.ru_maxrss - start_mem.ru_maxrss
            call_stats['memory'] = mem_delta / 1000.0

        else:
            call_stats['memory'] = -1

class TrafficLogger(Logger):
    def handle_request(self, event, call_stats):
        """
        Intercepts a new request creation and defines single request statistics
        used to metric time and performance.
        """
        req = event.request
        try:
            call_stats.update({
                "request_params": dict(req.params),
                "method": req.method,
            })
        except:
            pdb.set_trace()

    def handle_response(self, event, call_stats):
        resp = event.response
        try:
            call_stats['response_json_body'] = resp.json_body
        except:
            call_stats['response_json_body'] = ''

        call_stats['response_type'] = resp.content_type
        call_stats['response_status'] = resp.status_code
