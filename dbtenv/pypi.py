import http
import http.server
import json
import re
from typing import List, Union
import urllib.request

import dbtenv
from dbtenv import Version


logger = dbtenv.LOGGER


def get_pypi_package_metadata(package: str) -> str:
    package_json_url = f'https://pypi.org/pypi/{package}/json'
    logger.debug(f"Fetching {package} package metadata from {package_json_url}.")
    with urllib.request.urlopen(package_json_url) as package_json_response:
        return json.load(package_json_response)


def get_pypi_dbt_versions() -> List[Version]:
    package_metadata = get_pypi_package_metadata('dbt')
    possible_versions = ((Version(version), files) for version, files in package_metadata['releases'].items())
    return [version for version, files in possible_versions if any(not file['yanked'] for file in files)]


class BaseDateFilterPyPIRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP request handler that proxies PEP 503-compliant requests to pypi.org and excludes files uploaded after self.date.

    self.date needs to be manually defined when this class is subclassed (we can't pass the date to use via a
    constructor argument because the HTTPServer code instantiates request handlers in a very specific way).
    """

    def do_GET(self) -> None:
        logger.debug(f"Handling pypi.org request:  {self.requestline}")
        package_match = re.search(r'^/simple/(?P<package>[^/]+)', self.path)

        passthrough_request_headers = {
            header: value
            for header, value in self.headers.items()
            if header in ('User-Agent', 'Accept', 'Cache-Control')
        }
        pypi_request = urllib.request.Request(f'https://pypi.org{self.path}', headers=passthrough_request_headers)
        with urllib.request.urlopen(pypi_request) as pypi_response:
            pypi_response_status  = pypi_response.status
            pypi_response_headers = pypi_response.headers
            pypi_response_body    = pypi_response.read()

        if (pypi_response_status != http.HTTPStatus.OK or not package_match):
            logger.debug(f"Passing through pypi.org {pypi_response_status} response for {self.path}.")
            self.send_response(pypi_response_status)
            for header, value in pypi_response_headers.items():
                self.send_header(header, value)
            self.end_headers()
            self.wfile.write(pypi_response_body)
            return

        package = package_match['package']
        package_metadata = get_pypi_package_metadata(package)
        excluded_file_names = set(
            file['filename']
            for files in package_metadata['releases'].values()
            for file in files
            if file['upload_time'][:10] > self.date
        )
        file_link_pattern = r'<a href=[^>]+>(?P<file_name>[^<]+)</a>'
        excluded_file_link_count = 0
        def exclude_file_links(link_match: re.Match) -> str:
            nonlocal excluded_file_link_count
            if link_match['file_name'].strip() in excluded_file_names:
                excluded_file_link_count += 1
                return ''
            else:
                return link_match[0]
        modified_response_body = re.sub(file_link_pattern, exclude_file_links, pypi_response_body.decode('utf-8')).encode('utf-8')
        logger.debug(f"Excluded {excluded_file_link_count} files for {package} after {self.date}.")

        self.send_response(pypi_response_status)
        for header, value in pypi_response_headers.items():
            if header != 'Content-Length':
                self.send_header(header, value)
        self.send_header('Content-Length', len(modified_response_body))
        self.end_headers()
        self.wfile.write(modified_response_body)

    def log_request(self, code: Union[int, str] = '-', size: Union[int, str] = '-') -> None:
        # We're already logging requests in do_GET(), so don't log them again here.
        pass
