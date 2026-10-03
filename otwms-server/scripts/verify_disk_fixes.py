#!/usr/bin/env python3
"""Local isolated disk-fix regression; no Spring context, database or SSH."""

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", type=Path, default=Path(__file__).resolve().parents[1] / "otwms-backend")
    parser.add_argument("--maven-cache", type=Path, default=Path.home() / ".m2/repository")
    args = parser.parse_args()
    patterns = [
        "org/apache/poi/*/4.1.0/*.jar", "org/apache/xmlbeans/xmlbeans/3.1.0/*.jar",
        "org/apache/commons/commons-compress/1.18/*.jar",
        "org/apache/commons/commons-collections4/4.3/*.jar",
        "org/apache/commons/commons-math3/3.6.1/*.jar",
        "commons-codec/commons-codec/1.11/*.jar", "com/zaxxer/SparseBitSet/*/*.jar",
        "org/slf4j/slf4j-api/1.7.26/*.jar", "ch/qos/logback/*/1.2.3/*.jar",
    ]
    import os
    classpath = os.pathsep.join(str(path) for pattern in patterns for path in args.maven_cache.glob(pattern))
    prefix = "org/springblade/common/export/util/"
    sources = [args.backend / "src/main/java" / prefix / "WorkbookResources.java"]
    sources += [args.backend / "src/test/java" / prefix / (name + ".java") for name in
                ("WorkbookResourcesRegression", "LogbackDiskPolicyRegression")]
    xml = args.backend / "src/main/resources/log/logback-prod.xml"
    policy = ET.parse(xml).find("./appender/rollingPolicy")
    assert policy is not None
    assert policy.findtext("maxFileSize") == "100MB"
    assert policy.findtext("totalSizeCap") == "1GB"
    assert policy.findtext("maxHistory") == "7"
    with tempfile.TemporaryDirectory(prefix="otwms-disk-fix-tests-") as classes:
        subprocess.run(["javac", "--release", "8", "-proc:none", "-cp", classpath,
                        "-d", classes, *map(str, sources)], check=True)
        for name, extra in (("WorkbookResourcesRegression", []),
                            ("LogbackDiskPolicyRegression", [str(xml)])):
            subprocess.run(["java", "-cp", classes + os.pathsep + classpath,
                            "org.springblade.common.export.util." + name, *extra], check=True)
    check = Path(__file__).with_name("check_disk_pressure.py")
    ast.parse(check.read_text())
    spec = importlib.util.spec_from_file_location("disk_check", check)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    compile(module.REMOTE_COLLECTOR, "remote_collector", "exec")
    options = argparse.Namespace(critical_percent=95, warning_percent=80,
                                 log_warning_gib=10, tmp_file_warning=200000)
    sample = {"disk": {"used_percent": 22, "inode_used_percent": 2},
              "local_http": {"status": 200}, "tmp": {"files": 1},
              "java_processes": [{"stdout_application_log": {"append": False}}]}
    assert module.assess(sample, options)[0] == 1
    sample["disk"]["used_percent"] = 100
    assert module.assess(sample, options)[0] == 2
    print(json.dumps({"passed": True, "scope": "POI cleanup, Logback XML and disk assessment; not full application build"}))


if __name__ == "__main__":
    main()
