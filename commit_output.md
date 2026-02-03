# Git Commit Output
**Date:** Tue Feb  3 02:00:25 PM EET 2026

```
trim trailing whitespace.................................................Failed
- hook id: trailing-whitespace
- files were modified by this hook
fix end of files.........................................................Failed
- hook id: end-of-file-fixer
- files were modified by this hook
check yaml...............................................................Failed
- hook id: check-yaml
- files were modified by this hook
check toml...........................................(no files to check)Skipped
check json...........................................(no files to check)Skipped
check for added large files..............................................Failed
- hook id: check-added-large-files
- files were modified by this hook
check for case conflicts.................................................Failed
- hook id: check-case-conflict
- files were modified by this hook
check for merge conflicts................................................Failed
- hook id: check-merge-conflict
- files were modified by this hook
check for broken symlinks............................(no files to check)Skipped
check that executables have shebangs.....................................Failed
- hook id: check-executables-have-shebangs
- files were modified by this hook
check that scripts with shebangs are executable..........................Failed
- hook id: check-shebang-scripts-are-executable
- files were modified by this hook
detect private key.......................................................Failed
- hook id: detect-private-key
- files were modified by this hook
mixed line ending........................................................Failed
- hook id: mixed-line-ending
- files were modified by this hook
don't commit to branch...................................................Failed
- hook id: no-commit-to-branch
- files were modified by this hook
ruff.....................................................................Failed
- hook id: ruff
- exit code: 1
- files were modified by this hook

src/aegis/agent/graph.py:109:12: BLE001 Do not catch blind exception: `Exception`
    |
107 |             resp.raise_for_status()
108 |             payload = resp.json()
109 |     except Exception as exc:
    |            ^^^^^^^^^ BLE001
110 |         log.debug("loki_query_failed", error=str(exc))
111 |         return None
    |

src/aegis/agent/graph.py:120:30: PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
    |
118 |     for stream in results:
119 |         for value in stream.get("values", []):
120 |             if len(value) >= 2:
    |                              ^ PLR2004
121 |                 entries.append((value[0], value[1]))
122 |     if not entries:
    |

src/aegis/agent/graph.py:121:17: PERF401 Use `list.extend` to create a transformed list
    |
119 |         for value in stream.get("values", []):
120 |             if len(value) >= 2:
121 |                 entries.append((value[0], value[1]))
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ PERF401
122 |     if not entries:
123 |         return None
    |
    = help: Replace for loop with list.extend

src/aegis/cli.py:1714:22: PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
     |
1713 |     parts = value.split("/")
1714 |     if len(parts) != 2 or not parts[0] or not parts[1]:
     |                      ^ PLR2004
1715 |         console.print(
1716 |             "[bold red]Error:[/bold red] Resource must be in format: kind/name "
     |

src/aegis/cli.py:1754:9: S603 `subprocess` call: check for execution of untrusted input
     |
1752 |     ]
1753 |     with log_path.open("wb") as handle:
1754 |         subprocess.Popen(
     |         ^^^^^^^^^^^^^^^^ S603
1755 |             cmd,
1756 |             stdout=handle,
     |

src/aegis/k8s_operator/handlers/shadow.py:84:26: PLR2004 Magic value used in comparison, consider replacing `404` with a constant variable
   |
82 |         cm = api.read_namespaced_config_map(name, namespace)
83 |     except client.ApiException as exc:
84 |         if exc.status == 404:
   |                          ^^^ PLR2004
85 |             cm = client.V1ConfigMap(
86 |                 metadata=client.V1ObjectMeta(name=name, namespace=namespace),
   |

src/aegis/k8s_operator/handlers/shadow.py:115:26: PLR2004 Magic value used in comparison, consider replacing `404` with a constant variable
    |
113 |         api.patch_namespaced_config_map(name, namespace, body)
114 |     except client.ApiException as exc:
115 |         if exc.status == 404:
    |                          ^^^ PLR2004
116 |             cm = client.V1ConfigMap(
117 |                 metadata=client.V1ObjectMeta(name=name, namespace=namespace),
    |

src/aegis/k8s_operator/handlers/shadow.py:159:12: BLE001 Do not catch blind exception: `Exception`
    |
157 |     try:
158 |         from kubernetes.utils.quantity import parse_quantity
159 |     except Exception:
    |            ^^^^^^^^^ BLE001
160 |         parse_quantity = None
161 |     if parse_quantity:
    |

src/aegis/k8s_operator/handlers/shadow.py:164:16: BLE001 Do not catch blind exception: `Exception`
    |
162 |         try:
163 |             return float(parse_quantity(value))
164 |         except Exception:
    |                ^^^^^^^^^ BLE001
165 |             return 0.0
    |

src/aegis/k8s_operator/handlers/shadow.py:454:9: SIM108 Use ternary operator `names = set(indexed) if isinstance(indexed, list) else {indexed} if indexed else set()` instead of `if`-`else`-block
    |
452 |       for label_key, label_value in selector.items():
453 |           indexed = pod_by_label_index.get((namespace, label_key, label_value), [])
454 | /         if isinstance(indexed, list):
455 | |             names = set(indexed)
456 | |         else:
457 | |             names = {indexed} if indexed else set()
    | |___________________________________________________^ SIM108
458 |           matching_pods = names if matching_pods is None else matching_pods & names
    |
    = help: Replace `if`-`else`-block with `names = set(indexed) if isinstance(indexed, list) else {indexed} if indexed else set()`

src/aegis/security/falco.py:108:5: PLR0912 Too many branches (17 > 15)
    |
108 | def _filter_alerts(
    |     ^^^^^^^^^^^^^^ PLR0912
109 |     lines: list[str],
110 |     namespace: str,
    |

src/aegis/security/falco.py:363:9: TRY300 Consider moving this statement to an `else` block
    |
361 |             )
362 |
363 |         return result
    |         ^^^^^^^^^^^^^ TRY300
364 |
365 |     except OSError as e:
    |

src/aegis/security/pipeline.py:149:9: SIM108 Use ternary operator `image_list = [images] if isinstance(images, str) else list(images)` instead of `if`-`else`-block
    |
148 |           # Normalize input
149 | /         if isinstance(images, str):
150 | |             image_list = [images]
151 | |         else:
152 | |             image_list = list(images)
    | |_____________________________________^ SIM108
153 |
154 |           # Deduplicate images
    |
    = help: Replace `if`-`else`-block with `image_list = [images] if isinstance(images, str) else list(images)`

src/aegis/security/pipeline.py:296:5: SIM108 Use ternary operator `manifest_list = [manifests] if isinstance(manifests, str) else list(manifests)` instead of `if`-`else`-block
    |
294 |           List of unique container image references
295 |       """
296 | /     if isinstance(manifests, str):
297 | |         manifest_list = [manifests]
298 | |     else:
299 | |         manifest_list = list(manifests)
    | |_______________________________________^ SIM108
300 |
301 |       images: set[str] = set()
    |
    = help: Replace `if`-`else`-block with `manifest_list = [manifests] if isinstance(manifests, str) else list(manifests)`

src/aegis/shadow/manager.py:189:15: PLR0915 Too many statements (62 > 60)
    |
187 |         )
188 |
189 |     async def create_shadow(
    |               ^^^^^^^^^^^^^ PLR0915
190 |         self,
191 |         source_namespace: str,
    |

src/aegis/shadow/manager.py:352:15: PLR0912 Too many branches (24 > 15)
    |
350 |         return env
351 |
352 |     async def run_verification(
    |               ^^^^^^^^^^^^^^^^ PLR0912
353 |         self,
354 |         shadow_id: str,
    |

src/aegis/shadow/manager.py:352:15: PLR0915 Too many statements (99 > 60)
    |
350 |         return env
351 |
352 |     async def run_verification(
    |               ^^^^^^^^^^^^^^^^ PLR0915
353 |         self,
354 |         shadow_id: str,
    |

src/aegis/shadow/manager.py:653:17: TRY300 Consider moving this statement to an `else` block
    |
651 |                 env.status = ShadowStatus.READY
652 |                 await self._update_shadow_status(env)
653 |                 return env
    |                 ^^^^^^^^^^ TRY300
654 |             except Exception as exc:
655 |                 last_error = exc
    |

src/aegis/shadow/manager.py:654:20: BLE001 Do not catch blind exception: `Exception`
    |
652 |                 await self._update_shadow_status(env)
653 |                 return env
654 |             except Exception as exc:
    |                    ^^^^^^^^^ BLE001
655 |                 last_error = exc
656 |                 await asyncio.sleep(poll_interval)
    |

src/aegis/shadow/manager.py:739:9: SIM102 Use a single `if` statement instead of nested `if` statements
    |
737 |           )
738 |
739 | /         if env.status == ShadowStatus.CREATING and runtime == SandBoxRuntime.VCLUSTER.value:
740 | |             if self._vcluster_secret_exists(metadata.name):
    | |___________________________________________________________^ SIM102
741 |                   env.status = ShadowStatus.READY
    |
    = help: Combine `if` statements using `and`

src/aegis/shadow/manager.py:758:13: TRY300 Consider moving this statement to an `else` block
    |
756 |         try:
757 |             self._core_api.read_namespaced_secret(VCLUSTER_KUBECONFIG_NAME, namespace)
758 |             return True
    |             ^^^^^^^^^^^ TRY300
759 |         except ApiException as exc:
760 |             if exc.status == HTTP_NOT_FOUND:
    |

src/aegis/shadow/manager.py:879:30: PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
    |
877 |                 break
878 |             except RuntimeError as e:
879 |                 if attempt < 2:
    |                              ^ PLR2004
880 |                     log.debug(
881 |                         "vcluster_kubeconfig_secret_retry",
    |

src/aegis/shadow/manager.py:902:17: TRY400 Use `logging.exception` instead of `logging.error`
    |
900 |                   log.info("vcluster_kubeconfig_loaded", source="cli", shadow=name)
901 |               except RuntimeError as e:
902 | /                 log.error(
903 | |                     "vcluster_kubeconfig_cli_failed",
904 | |                     shadow=name,
905 | |                     namespace=namespace,
906 | |                     error=str(e),
907 | |                 )
    | |_________________^ TRY400
908 |                   raise
    |
    = help: Replace with `exception`

src/aegis/shadow/manager.py:1381:20: BLE001 Do not catch blind exception: `Exception`
     |
1379 |                 await asyncio.sleep(poll_interval)
1380 |
1381 |             except Exception as e:
     |                    ^^^^^^^^^ BLE001
1382 |                 log.debug(
1383 |                     "vcluster_resources_check_error",
     |

src/aegis/shadow/manager.py:2357:23: C401 Unnecessary generator (rewrite as a set comprehension)
     |
2355 |             log.warning("shadow_image_resolution_failed", shadow_id=env.id, error=str(exc))
2356 |
2357 |         return sorted(set(i for i in images if i))
     |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^ C401
2358 |
2359 |     @staticmethod
     |
     = help: Rewrite as a set comprehension

src/aegis/shadow/manager.py:2366:17: PERF401 Use a list comprehension to create a transformed list
     |
2364 |         for container in spec.containers or []:
2365 |             if container.image:
2366 |                 images.append(container.image)
     |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ PERF401
2367 |         for container in spec.init_containers or []:
2368 |             if container.image:
     |
     = help: Replace for loop with list comprehension

src/aegis/shadow/manager.py:2369:17: PERF401 Use `list.extend` to create a transformed list
     |
2367 |         for container in spec.init_containers or []:
2368 |             if container.image:
2369 |                 images.append(container.image)
     |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ PERF401
2370 |         return images
     |
     = help: Replace for loop with list.extend

src/aegis/utils/gpu.py:46:9: SIM102 Use a single `if` statement instead of nested `if` statements
   |
44 |       for node in nodes.items:
45 |           allocatable: dict[str, Any] = node.status.allocatable or {}
46 | /         if any(
47 | |             key in allocatable and allocatable[key] not in ("0", 0) for key in GPU_RESOURCE_KEYS
48 | |         ):
49 | |             if node.metadata and node.metadata.name:
   | |____________________________________________________^ SIM102
50 |                   gpu_nodes.append(node.metadata.name)
51 |       return gpu_nodes
   |
   = help: Combine `if` statements using `and`

tests/integration/test_end_to_end_workflow.py:16:1: ERA001 Found commented-out code
   |
14 | # """
15 |
16 | # from __future__ import annotations
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
17 |
18 | # import json
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:18:1: ERA001 Found commented-out code
   |
16 | # from __future__ import annotations
17 |
18 | # import json
   | ^^^^^^^^^^^^^ ERA001
19 | # import os
20 | # import subprocess
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:19:1: ERA001 Found commented-out code
   |
18 | # import json
19 | # import os
   | ^^^^^^^^^^^ ERA001
20 | # import subprocess
21 | # from dataclasses import dataclass
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:20:1: ERA001 Found commented-out code
   |
18 | # import json
19 | # import os
20 | # import subprocess
   | ^^^^^^^^^^^^^^^^^^^ ERA001
21 | # from dataclasses import dataclass
22 | # from datetime import UTC, datetime
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:21:1: ERA001 Found commented-out code
   |
19 | # import os
20 | # import subprocess
21 | # from dataclasses import dataclass
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
22 | # from datetime import UTC, datetime
23 | # from typing import Any
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:22:1: ERA001 Found commented-out code
   |
20 | # import subprocess
21 | # from dataclasses import dataclass
22 | # from datetime import UTC, datetime
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
23 | # from typing import Any
24 | # from unittest.mock import MagicMock, patch
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:23:1: ERA001 Found commented-out code
   |
21 | # from dataclasses import dataclass
22 | # from datetime import UTC, datetime
23 | # from typing import Any
   | ^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
24 | # from unittest.mock import MagicMock, patch
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:24:1: ERA001 Found commented-out code
   |
22 | # from datetime import UTC, datetime
23 | # from typing import Any
24 | # from unittest.mock import MagicMock, patch
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
25 |
26 | # import pytest
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:26:1: ERA001 Found commented-out code
   |
24 | # from unittest.mock import MagicMock, patch
25 |
26 | # import pytest
   | ^^^^^^^^^^^^^^^ ERA001
27 | # from kubernetes import config as kubernetes_config
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:27:1: ERA001 Found commented-out code
   |
26 | # import pytest
27 | # from kubernetes import config as kubernetes_config
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
28 |
29 | # from aegis.agent.graph import analyze_incident
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:29:1: ERA001 Found commented-out code
   |
27 | # from kubernetes import config as kubernetes_config
28 |
29 | # from aegis.agent.graph import analyze_incident
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
30 | # from aegis.agent.state import (
31 | #     FixProposal,
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:36:1: ERA001 Found commented-out code
   |
34 | #     RCAResult,
35 | #     VerificationPlan,
36 | # )
   | ^^^ ERA001
37 | # from aegis.config.settings import settings
38 | # from aegis.crd import FixProposal as CRDFixProposal
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:37:1: ERA001 Found commented-out code
   |
35 | #     VerificationPlan,
36 | # )
37 | # from aegis.config.settings import settings
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
38 | # from aegis.crd import FixProposal as CRDFixProposal
39 | # from aegis.crd import FixType as CRDFixType
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:38:1: ERA001 Found commented-out code
   |
36 | # )
37 | # from aegis.config.settings import settings
38 | # from aegis.crd import FixProposal as CRDFixProposal
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
39 | # from aegis.crd import FixType as CRDFixType
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:39:1: ERA001 Found commented-out code
   |
37 | # from aegis.config.settings import settings
38 | # from aegis.crd import FixProposal as CRDFixProposal
39 | # from aegis.crd import FixType as CRDFixType
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:51:1: ERA001 Found commented-out code
   |
49 | #     """Mock context for cluster operations."""
50 |
51 | #     minikube_running: bool = True
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
52 | #     docker_compose_running: bool = True
53 | #     ollama_available: bool = True
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:52:1: ERA001 Found commented-out code
   |
51 | #     minikube_running: bool = True
52 | #     docker_compose_running: bool = True
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
53 | #     ollama_available: bool = True
54 | #     k8sgpt_installed: bool = True
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:53:1: ERA001 Found commented-out code
   |
51 | #     minikube_running: bool = True
52 | #     docker_compose_running: bool = True
53 | #     ollama_available: bool = True
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
54 | #     k8sgpt_installed: bool = True
55 | #     vcluster_installed: bool = True
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:54:1: ERA001 Found commented-out code
   |
52 | #     docker_compose_running: bool = True
53 | #     ollama_available: bool = True
54 | #     k8sgpt_installed: bool = True
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
55 | #     vcluster_installed: bool = True
56 | #     prometheus_up: bool = True
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:55:1: ERA001 Found commented-out code
   |
53 | #     ollama_available: bool = True
54 | #     k8sgpt_installed: bool = True
55 | #     vcluster_installed: bool = True
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
56 | #     prometheus_up: bool = True
57 | #     grafana_up: bool = True
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:56:1: ERA001 Found commented-out code
   |
54 | #     k8sgpt_installed: bool = True
55 | #     vcluster_installed: bool = True
56 | #     prometheus_up: bool = True
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
57 | #     grafana_up: bool = True
58 | #     loki_up: bool = True
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:57:1: ERA001 Found commented-out code
   |
55 | #     vcluster_installed: bool = True
56 | #     prometheus_up: bool = True
57 | #     grafana_up: bool = True
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
58 | #     loki_up: bool = True
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:58:1: ERA001 Found commented-out code
   |
56 | #     prometheus_up: bool = True
57 | #     grafana_up: bool = True
58 | #     loki_up: bool = True
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:64:1: ERA001 Found commented-out code
   |
62 | # def mock_cluster_context() -> MockClusterContext:
63 | #     """Provide mock cluster context for testing."""
64 | #     return MockClusterContext()
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:74:1: ERA001 Found commented-out code
   |
72 | #         patch("aegis.kubernetes.fix_applier.client") as client_mod,
73 | #     ):
74 | #         config.ConfigException = kubernetes_config.ConfigException
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
75 | #         config.load_incluster_config.side_effect = kubernetes_config.ConfigException(
76 | #             "Not in cluster",
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:77:1: ERA001 Found commented-out code
   |
75 | #         config.load_incluster_config.side_effect = kubernetes_config.ConfigException(
76 | #             "Not in cluster",
77 | #         )
   | ^^^^^^^^^^^ ERA001
78 | #         config.load_kube_config.return_value = None
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:78:1: ERA001 Found commented-out code
   |
76 | #             "Not in cluster",
77 | #         )
78 | #         config.load_kube_config.return_value = None
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
79 |
80 | #         mock_apps = MagicMock()
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:80:1: ERA001 Found commented-out code
   |
78 | #         config.load_kube_config.return_value = None
79 |
80 | #         mock_apps = MagicMock()
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
81 | #         mock_core = MagicMock()
82 | #         mock_custom = MagicMock()
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:81:1: ERA001 Found commented-out code
   |
80 | #         mock_apps = MagicMock()
81 | #         mock_core = MagicMock()
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
82 | #         mock_custom = MagicMock()
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:82:1: ERA001 Found commented-out code
   |
80 | #         mock_apps = MagicMock()
81 | #         mock_core = MagicMock()
82 | #         mock_custom = MagicMock()
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
83 |
84 | #         # Mock deployment for restart operations
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:85:1: ERA001 Found commented-out code
   |
84 | #         # Mock deployment for restart operations
85 | #         mock_deployment = MagicMock()
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
86 | #         mock_deployment.metadata.resource_version = "1000"
87 | #         mock_deployment.spec.replicas = 3
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:86:1: ERA001 Found commented-out code
   |
84 | #         # Mock deployment for restart operations
85 | #         mock_deployment = MagicMock()
86 | #         mock_deployment.metadata.resource_version = "1000"
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
87 | #         mock_deployment.spec.replicas = 3
88 | #         mock_deployment.spec.template.spec.containers = [MagicMock()]
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:87:1: ERA001 Found commented-out code
   |
85 | #         mock_deployment = MagicMock()
86 | #         mock_deployment.metadata.resource_version = "1000"
87 | #         mock_deployment.spec.replicas = 3
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
88 | #         mock_deployment.spec.template.spec.containers = [MagicMock()]
89 | #         mock_deployment.spec.template.spec.containers[0].name = "app"
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:88:1: ERA001 Found commented-out code
   |
86 | #         mock_deployment.metadata.resource_version = "1000"
87 | #         mock_deployment.spec.replicas = 3
88 | #         mock_deployment.spec.template.spec.containers = [MagicMock()]
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
89 | #         mock_deployment.spec.template.spec.containers[0].name = "app"
90 | #         mock_deployment.spec.selector.match_labels = {"app": "test"}
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:89:1: ERA001 Found commented-out code
   |
87 | #         mock_deployment.spec.replicas = 3
88 | #         mock_deployment.spec.template.spec.containers = [MagicMock()]
89 | #         mock_deployment.spec.template.spec.containers[0].name = "app"
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
90 | #         mock_deployment.spec.selector.match_labels = {"app": "test"}
91 | #         mock_apps.read_namespaced_deployment.return_value = mock_deployment
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:90:1: ERA001 Found commented-out code
   |
88 | #         mock_deployment.spec.template.spec.containers = [MagicMock()]
89 | #         mock_deployment.spec.template.spec.containers[0].name = "app"
90 | #         mock_deployment.spec.selector.match_labels = {"app": "test"}
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
91 | #         mock_apps.read_namespaced_deployment.return_value = mock_deployment
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:91:1: ERA001 Found commented-out code
   |
89 | #         mock_deployment.spec.template.spec.containers[0].name = "app"
90 | #         mock_deployment.spec.selector.match_labels = {"app": "test"}
91 | #         mock_apps.read_namespaced_deployment.return_value = mock_deployment
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
92 |
93 | #         # Mock successful patch
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:94:1: ERA001 Found commented-out code
   |
93 | #         # Mock successful patch
94 | #         mock_updated = MagicMock()
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
95 | #         mock_updated.metadata.resource_version = "1001"
96 | #         mock_apps.patch_namespaced_deployment.return_value = mock_updated
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:95:1: ERA001 Found commented-out code
   |
93 | #         # Mock successful patch
94 | #         mock_updated = MagicMock()
95 | #         mock_updated.metadata.resource_version = "1001"
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
96 | #         mock_apps.patch_namespaced_deployment.return_value = mock_updated
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:96:1: ERA001 Found commented-out code
   |
94 | #         mock_updated = MagicMock()
95 | #         mock_updated.metadata.resource_version = "1001"
96 | #         mock_apps.patch_namespaced_deployment.return_value = mock_updated
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
97 |
98 | #         client_mod.AppsV1Api.return_value = mock_apps
   |
   = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:98:1: ERA001 Found commented-out code
    |
 96 | #         mock_apps.patch_namespaced_deployment.return_value = mock_updated
 97 |
 98 | #         client_mod.AppsV1Api.return_value = mock_apps
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
 99 | #         client_mod.CoreV1Api.return_value = mock_core
100 | #         client_mod.CustomObjectsApi.return_value = mock_custom
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:99:1: ERA001 Found commented-out code
    |
 98 | #         client_mod.AppsV1Api.return_value = mock_apps
 99 | #         client_mod.CoreV1Api.return_value = mock_core
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
100 | #         client_mod.CustomObjectsApi.return_value = mock_custom
101 | #         client_mod.ApiException = Exception
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:100:1: ERA001 Found commented-out code
    |
 98 | #         client_mod.AppsV1Api.return_value = mock_apps
 99 | #         client_mod.CoreV1Api.return_value = mock_core
100 | #         client_mod.CustomObjectsApi.return_value = mock_custom
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
101 | #         client_mod.ApiException = Exception
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:101:1: ERA001 Found commented-out code
    |
 99 | #         client_mod.CoreV1Api.return_value = mock_core
100 | #         client_mod.CustomObjectsApi.return_value = mock_custom
101 | #         client_mod.ApiException = Exception
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
102 |
103 | #         yield {
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:104:1: ERA001 Found commented-out code
    |
103 | #         yield {
104 | #             "apps": mock_apps,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
105 | #             "core": mock_core,
106 | #             "custom": mock_custom,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:105:1: ERA001 Found commented-out code
    |
103 | #         yield {
104 | #             "apps": mock_apps,
105 | #             "core": mock_core,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
106 | #             "custom": mock_custom,
107 | #             "config": config,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:106:1: ERA001 Found commented-out code
    |
104 | #             "apps": mock_apps,
105 | #             "core": mock_core,
106 | #             "custom": mock_custom,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
107 | #             "config": config,
108 | #         }
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:107:1: ERA001 Found commented-out code
    |
105 | #             "core": mock_core,
106 | #             "custom": mock_custom,
107 | #             "config": config,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
108 | #         }
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:108:1: ERA001 Found commented-out code
    |
106 | #             "custom": mock_custom,
107 | #             "config": config,
108 | #         }
    | ^^^^^^^^^^^ ERA001
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:115:1: ERA001 Found commented-out code
    |
113 | #     """Mock Ollama client for LLM operations."""
114 | #     with patch("aegis.agent.llm.ollama.get_ollama_client") as mock_get:
115 | #         mock_client = MagicMock()
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
116 | #         mock_client.is_available.return_value = True
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:116:1: ERA001 Found commented-out code
    |
114 | #     with patch("aegis.agent.llm.ollama.get_ollama_client") as mock_get:
115 | #         mock_client = MagicMock()
116 | #         mock_client.is_available.return_value = True
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
117 |
118 | #         # Mock RCA result
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:119:1: ERA001 Found commented-out code
    |
118 | #         # Mock RCA result
119 | #         mock_rca = RCAResult(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
120 | #             root_cause="Container OOMKilled due to memory limit exceeded",
121 | #             severity=IncidentSeverity.HIGH,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:120:1: ERA001 Found commented-out code
    |
118 | #         # Mock RCA result
119 | #         mock_rca = RCAResult(
120 | #             root_cause="Container OOMKilled due to memory limit exceeded",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
121 | #             severity=IncidentSeverity.HIGH,
122 | #             confidence_score=0.92,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:121:1: ERA001 Found commented-out code
    |
119 | #         mock_rca = RCAResult(
120 | #             root_cause="Container OOMKilled due to memory limit exceeded",
121 | #             severity=IncidentSeverity.HIGH,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
122 | #             confidence_score=0.92,
123 | #             reasoning="The pod shows repeated OOMKilled events with memory usage spikes",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:122:1: ERA001 Found commented-out code
    |
120 | #             root_cause="Container OOMKilled due to memory limit exceeded",
121 | #             severity=IncidentSeverity.HIGH,
122 | #             confidence_score=0.92,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
123 | #             reasoning="The pod shows repeated OOMKilled events with memory usage spikes",
124 | #             analysis_steps=[
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:123:1: ERA001 Found commented-out code
    |
121 | #             severity=IncidentSeverity.HIGH,
122 | #             confidence_score=0.92,
123 | #             reasoning="The pod shows repeated OOMKilled events with memory usage spikes",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
124 | #             analysis_steps=[
125 | #                 "Reviewed pod logs for OOMKilled events",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:124:1: ERA001 Found commented-out code
    |
122 | #             confidence_score=0.92,
123 | #             reasoning="The pod shows repeated OOMKilled events with memory usage spikes",
124 | #             analysis_steps=[
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
125 | #                 "Reviewed pod logs for OOMKilled events",
126 | #                 "Analyzed memory usage patterns",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:129:1: ERA001 Found commented-out code
    |
127 | #                 "Identified memory leak in application",
128 | #             ],
129 | #             evidence_summary=[
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
130 | #                 "Container restart count: 5",
131 | #                 "OOMKilled termination reason in pod status",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:130:1: ERA001 Found commented-out code
    |
128 | #             ],
129 | #             evidence_summary=[
130 | #                 "Container restart count: 5",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
131 | #                 "OOMKilled termination reason in pod status",
132 | #                 "Memory usage at 99% before kill",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:132:1: ERA001 Found commented-out code
    |
130 | #                 "Container restart count: 5",
131 | #                 "OOMKilled termination reason in pod status",
132 | #                 "Memory usage at 99% before kill",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
133 | #             ],
134 | #             decision_rationale="High confidence based on clear OOMKilled evidence",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:134:1: ERA001 Found commented-out code
    |
132 | #                 "Memory usage at 99% before kill",
133 | #             ],
134 | #             decision_rationale="High confidence based on clear OOMKilled evidence",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
135 | #             affected_components=["pod/demo-api-xxx", "container/app"],
136 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:135:1: ERA001 Found commented-out code
    |
133 | #             ],
134 | #             decision_rationale="High confidence based on clear OOMKilled evidence",
135 | #             affected_components=["pod/demo-api-xxx", "container/app"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
136 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:136:1: ERA001 Found commented-out code
    |
134 | #             decision_rationale="High confidence based on clear OOMKilled evidence",
135 | #             affected_components=["pod/demo-api-xxx", "container/app"],
136 | #         )
    | ^^^^^^^^^^^ ERA001
137 |
138 | #         # Mock Fix Proposal
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:139:1: ERA001 Found commented-out code
    |
138 | #         # Mock Fix Proposal
139 | #         mock_fix = FixProposal(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
140 | #             fix_type=FixType.PATCH,
141 | #             description="Increase memory limit from 256Mi to 512Mi",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:140:1: ERA001 Found commented-out code
    |
138 | #         # Mock Fix Proposal
139 | #         mock_fix = FixProposal(
140 | #             fix_type=FixType.PATCH,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
141 | #             description="Increase memory limit from 256Mi to 512Mi",
142 | #             commands=["kubectl set resources deployment/demo-api --limits=memory=512Mi"],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:141:1: ERA001 Found commented-out code
    |
139 | #         mock_fix = FixProposal(
140 | #             fix_type=FixType.PATCH,
141 | #             description="Increase memory limit from 256Mi to 512Mi",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
142 | #             commands=["kubectl set resources deployment/demo-api --limits=memory=512Mi"],
143 | #             confidence_score=0.88,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:142:1: ERA001 Found commented-out code
    |
140 | #             fix_type=FixType.PATCH,
141 | #             description="Increase memory limit from 256Mi to 512Mi",
142 | #             commands=["kubectl set resources deployment/demo-api --limits=memory=512Mi"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
143 | #             confidence_score=0.88,
144 | #             risks=["May increase cluster resource usage"],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:143:1: ERA001 Found commented-out code
    |
141 | #             description="Increase memory limit from 256Mi to 512Mi",
142 | #             commands=["kubectl set resources deployment/demo-api --limits=memory=512Mi"],
143 | #             confidence_score=0.88,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
144 | #             risks=["May increase cluster resource usage"],
145 | #             estimated_downtime="0s - rolling update",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:144:1: ERA001 Found commented-out code
    |
142 | #             commands=["kubectl set resources deployment/demo-api --limits=memory=512Mi"],
143 | #             confidence_score=0.88,
144 | #             risks=["May increase cluster resource usage"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
145 | #             estimated_downtime="0s - rolling update",
146 | #             rollback_commands=["kubectl set resources deployment/demo-api --limits=memory=256Mi"],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:145:1: ERA001 Found commented-out code
    |
143 | #             confidence_score=0.88,
144 | #             risks=["May increase cluster resource usage"],
145 | #             estimated_downtime="0s - rolling update",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
146 | #             rollback_commands=["kubectl set resources deployment/demo-api --limits=memory=256Mi"],
147 | #             manifests={},
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:146:1: ERA001 Found commented-out code
    |
144 | #             risks=["May increase cluster resource usage"],
145 | #             estimated_downtime="0s - rolling update",
146 | #             rollback_commands=["kubectl set resources deployment/demo-api --limits=memory=256Mi"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
147 | #             manifests={},
148 | #             analysis_steps=[
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:147:1: ERA001 Found commented-out code
    |
145 | #             estimated_downtime="0s - rolling update",
146 | #             rollback_commands=["kubectl set resources deployment/demo-api --limits=memory=256Mi"],
147 | #             manifests={},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
148 | #             analysis_steps=[
149 | #                 "Analyzed current resource limits",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:148:1: ERA001 Found commented-out code
    |
146 | #             rollback_commands=["kubectl set resources deployment/demo-api --limits=memory=256Mi"],
147 | #             manifests={},
148 | #             analysis_steps=[
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
149 | #                 "Analyzed current resource limits",
150 | #                 "Calculated required memory headroom",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:153:1: ERA001 Found commented-out code
    |
151 | #                 "Prepared resource adjustment patch",
152 | #             ],
153 | #             decision_rationale="Memory limit increase is the most direct fix for OOMKilled",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
154 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:154:1: ERA001 Found commented-out code
    |
152 | #             ],
153 | #             decision_rationale="Memory limit increase is the most direct fix for OOMKilled",
154 | #         )
    | ^^^^^^^^^^^ ERA001
155 |
156 | #         # Mock Verification Plan
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:157:1: ERA001 Found commented-out code
    |
156 | #         # Mock Verification Plan
157 | #         mock_verify = VerificationPlan(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
158 | #             verification_type="shadow",
159 | #             duration=60,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:158:1: ERA001 Found commented-out code
    |
156 | #         # Mock Verification Plan
157 | #         mock_verify = VerificationPlan(
158 | #             verification_type="shadow",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
159 | #             duration=60,
160 | #             test_scenarios=["Memory stress test", "Load test with concurrent users"],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:159:1: ERA001 Found commented-out code
    |
157 | #         mock_verify = VerificationPlan(
158 | #             verification_type="shadow",
159 | #             duration=60,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
160 | #             test_scenarios=["Memory stress test", "Load test with concurrent users"],
161 | #             success_criteria=["No OOMKilled events", "Memory usage < 80%"],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:160:1: ERA001 Found commented-out code
    |
158 | #             verification_type="shadow",
159 | #             duration=60,
160 | #             test_scenarios=["Memory stress test", "Load test with concurrent users"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
161 | #             success_criteria=["No OOMKilled events", "Memory usage < 80%"],
162 | #             analysis_steps=["Created shadow environment", "Deployed fix for testing"],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:161:1: ERA001 Found commented-out code
    |
159 | #             duration=60,
160 | #             test_scenarios=["Memory stress test", "Load test with concurrent users"],
161 | #             success_criteria=["No OOMKilled events", "Memory usage < 80%"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
162 | #             analysis_steps=["Created shadow environment", "Deployed fix for testing"],
163 | #             decision_rationale="Shadow verification ensures fix works before production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:162:1: ERA001 Found commented-out code
    |
160 | #             test_scenarios=["Memory stress test", "Load test with concurrent users"],
161 | #             success_criteria=["No OOMKilled events", "Memory usage < 80%"],
162 | #             analysis_steps=["Created shadow environment", "Deployed fix for testing"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
163 | #             decision_rationale="Shadow verification ensures fix works before production",
164 | #             rollback_on_failure=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:163:1: ERA001 Found commented-out code
    |
161 | #             success_criteria=["No OOMKilled events", "Memory usage < 80%"],
162 | #             analysis_steps=["Created shadow environment", "Deployed fix for testing"],
163 | #             decision_rationale="Shadow verification ensures fix works before production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
164 | #             rollback_on_failure=True,
165 | #             security_checks=[],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:164:1: ERA001 Found commented-out code
    |
162 | #             analysis_steps=["Created shadow environment", "Deployed fix for testing"],
163 | #             decision_rationale="Shadow verification ensures fix works before production",
164 | #             rollback_on_failure=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
165 | #             security_checks=[],
166 | #             approval_required=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:165:1: ERA001 Found commented-out code
    |
163 | #             decision_rationale="Shadow verification ensures fix works before production",
164 | #             rollback_on_failure=True,
165 | #             security_checks=[],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
166 | #             approval_required=True,
167 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:166:1: ERA001 Found commented-out code
    |
164 | #             rollback_on_failure=True,
165 | #             security_checks=[],
166 | #             approval_required=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
167 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:167:1: ERA001 Found commented-out code
    |
165 | #             security_checks=[],
166 | #             approval_required=True,
167 | #         )
    | ^^^^^^^^^^^ ERA001
168 |
169 | #         def chat_with_schema_side_effect(messages, schema, **kwargs):
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:171:1: ERA001 Found commented-out code
    |
169 | #         def chat_with_schema_side_effect(messages, schema, **kwargs):
170 | #             if schema.__name__ == "RCAResult":
171 | #                 return mock_rca
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
172 | #             if schema.__name__ == "FixProposal":
173 | #                 return mock_fix
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:173:1: ERA001 Found commented-out code
    |
171 | #                 return mock_rca
172 | #             if schema.__name__ == "FixProposal":
173 | #                 return mock_fix
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
174 | #             if schema.__name__ == "VerificationPlan":
175 | #                 return mock_verify
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:175:1: ERA001 Found commented-out code
    |
173 | #                 return mock_fix
174 | #             if schema.__name__ == "VerificationPlan":
175 | #                 return mock_verify
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
176 | #             return None
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:176:1: ERA001 Found commented-out code
    |
174 | #             if schema.__name__ == "VerificationPlan":
175 | #                 return mock_verify
176 | #             return None
    | ^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
177 |
178 | #         mock_client.chat_with_schema.side_effect = chat_with_schema_side_effect
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:178:1: ERA001 Found commented-out code
    |
176 | #             return None
177 |
178 | #         mock_client.chat_with_schema.side_effect = chat_with_schema_side_effect
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
179 | #         mock_get.return_value = mock_client
180 | #         yield mock_client
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:179:1: ERA001 Found commented-out code
    |
178 | #         mock_client.chat_with_schema.side_effect = chat_with_schema_side_effect
179 | #         mock_get.return_value = mock_client
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
180 | #         yield mock_client
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:187:1: ERA001 Found commented-out code
    |
185 | #     """Mock K8sGPT analyzer."""
186 | #     with patch("aegis.agent.analyzer.K8sGPTAnalyzer") as mock_class:
187 | #         mock_analyzer = MagicMock()
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
188 | #         mock_analyzer.is_available = True
189 | #         mock_analyzer.backend = "ollama"
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:188:1: ERA001 Found commented-out code
    |
186 | #     with patch("aegis.agent.analyzer.K8sGPTAnalyzer") as mock_class:
187 | #         mock_analyzer = MagicMock()
188 | #         mock_analyzer.is_available = True
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
189 | #         mock_analyzer.backend = "ollama"
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:189:1: ERA001 Found commented-out code
    |
187 | #         mock_analyzer = MagicMock()
188 | #         mock_analyzer.is_available = True
189 | #         mock_analyzer.backend = "ollama"
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
190 |
191 | #         async def mock_analyze(*args, **kwargs):
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:192:1: ERA001 Found commented-out code
    |
191 | #         async def mock_analyze(*args, **kwargs):
192 | #             from aegis.agent.state import K8sGPTAnalysis, K8sGPTError, K8sGPTResult
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
193 |
194 | #             return K8sGPTAnalysis(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:195:1: ERA001 Found commented-out code
    |
194 | #             return K8sGPTAnalysis(
195 | #                 status="Unhealthy",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
196 | #                 problems=1,
197 | #                 results=[
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:196:1: ERA001 Found commented-out code
    |
194 | #             return K8sGPTAnalysis(
195 | #                 status="Unhealthy",
196 | #                 problems=1,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
197 | #                 results=[
198 | #                     K8sGPTResult(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:197:1: ERA001 Found commented-out code
    |
195 | #                 status="Unhealthy",
196 | #                 problems=1,
197 | #                 results=[
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
198 | #                     K8sGPTResult(
199 | #                         name="demo-api-xxx",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:199:1: ERA001 Found commented-out code
    |
197 | #                 results=[
198 | #                     K8sGPTResult(
199 | #                         name="demo-api-xxx",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
200 | #                         kind="Pod",
201 | #                         error=[
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:200:1: ERA001 Found commented-out code
    |
198 | #                     K8sGPTResult(
199 | #                         name="demo-api-xxx",
200 | #                         kind="Pod",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
201 | #                         error=[
202 | #                             K8sGPTError(Text="Container OOMKilled"),
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:201:1: ERA001 Found commented-out code
    |
199 | #                         name="demo-api-xxx",
200 | #                         kind="Pod",
201 | #                         error=[
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
202 | #                             K8sGPTError(Text="Container OOMKilled"),
203 | #                             K8sGPTError(Text="Memory limit exceeded"),
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:202:1: ERA001 Found commented-out code
    |
200 | #                         kind="Pod",
201 | #                         error=[
202 | #                             K8sGPTError(Text="Container OOMKilled"),
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
203 | #                             K8sGPTError(Text="Memory limit exceeded"),
204 | #                         ],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:203:1: ERA001 Found commented-out code
    |
201 | #                         error=[
202 | #                             K8sGPTError(Text="Container OOMKilled"),
203 | #                             K8sGPTError(Text="Memory limit exceeded"),
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
204 | #                         ],
205 | #                         parentObject="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:205:1: ERA001 Found commented-out code
    |
203 | #                             K8sGPTError(Text="Memory limit exceeded"),
204 | #                         ],
205 | #                         parentObject="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
206 | #                     ),
207 | #                 ],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:208:1: ERA001 Found commented-out code
    |
206 | #                     ),
207 | #                 ],
208 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
209 |
210 | #         mock_analyzer.analyze = mock_analyze
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:210:1: ERA001 Found commented-out code
    |
208 | #             )
209 |
210 | #         mock_analyzer.analyze = mock_analyze
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
211 | #         mock_class.return_value = mock_analyzer
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:211:1: ERA001 Found commented-out code
    |
210 | #         mock_analyzer.analyze = mock_analyze
211 | #         mock_class.return_value = mock_analyzer
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
212 |
213 | #         with patch("aegis.agent.analyzer.get_k8sgpt_analyzer", return_value=mock_analyzer):
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:221:1: ERA001 Found commented-out code
    |
219 | #     """Mock shadow manager for vCluster operations."""
220 | #     with patch("aegis.shadow.manager.ShadowManager") as mock_class:
221 | #         mock_manager = MagicMock()
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
222 | #         mock_manager.runtime = "vcluster"
223 | #         mock_manager.active_count = 0
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:222:1: ERA001 Found commented-out code
    |
220 | #     with patch("aegis.shadow.manager.ShadowManager") as mock_class:
221 | #         mock_manager = MagicMock()
222 | #         mock_manager.runtime = "vcluster"
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
223 | #         mock_manager.active_count = 0
224 | #         mock_manager.max_concurrent = 3
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:223:1: ERA001 Found commented-out code
    |
221 | #         mock_manager = MagicMock()
222 | #         mock_manager.runtime = "vcluster"
223 | #         mock_manager.active_count = 0
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
224 | #         mock_manager.max_concurrent = 3
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:224:1: ERA001 Found commented-out code
    |
222 | #         mock_manager.runtime = "vcluster"
223 | #         mock_manager.active_count = 0
224 | #         mock_manager.max_concurrent = 3
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
225 |
226 | #         async def mock_create_shadow(*args, **kwargs):
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:227:1: ERA001 Found commented-out code
    |
226 | #         async def mock_create_shadow(*args, **kwargs):
227 | #             from aegis.shadow.manager import ShadowEnvironment, ShadowStatus
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
228 |
229 | #             return ShadowEnvironment(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:230:1: ERA001 Found commented-out code
    |
229 | #             return ShadowEnvironment(
230 | #                 id="demo-api-20260202-120000",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
231 | #                 namespace="default",
232 | #                 source_namespace="default",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:231:1: ERA001 Found commented-out code
    |
229 | #             return ShadowEnvironment(
230 | #                 id="demo-api-20260202-120000",
231 | #                 namespace="default",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
232 | #                 source_namespace="default",
233 | #                 source_resource="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:232:1: ERA001 Found commented-out code
    |
230 | #                 id="demo-api-20260202-120000",
231 | #                 namespace="default",
232 | #                 source_namespace="default",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
233 | #                 source_resource="demo-api",
234 | #                 source_resource_kind="Deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:233:1: ERA001 Found commented-out code
    |
231 | #                 namespace="default",
232 | #                 source_namespace="default",
233 | #                 source_resource="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
234 | #                 source_resource_kind="Deployment",
235 | #                 status=ShadowStatus.READY,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:234:1: ERA001 Found commented-out code
    |
232 | #                 source_namespace="default",
233 | #                 source_resource="demo-api",
234 | #                 source_resource_kind="Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
235 | #                 status=ShadowStatus.READY,
236 | #                 runtime="vcluster",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:235:1: ERA001 Found commented-out code
    |
233 | #                 source_resource="demo-api",
234 | #                 source_resource_kind="Deployment",
235 | #                 status=ShadowStatus.READY,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
236 | #                 runtime="vcluster",
237 | #                 health_score=0.95,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:236:1: ERA001 Found commented-out code
    |
234 | #                 source_resource_kind="Deployment",
235 | #                 status=ShadowStatus.READY,
236 | #                 runtime="vcluster",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
237 | #                 health_score=0.95,
238 | #                 logs=[
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:237:1: ERA001 Found commented-out code
    |
235 | #                 status=ShadowStatus.READY,
236 | #                 runtime="vcluster",
237 | #                 health_score=0.95,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
238 | #                 logs=[
239 | #                     "Creating shadow environment: demo-api-20260202-120000",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:238:1: ERA001 Found commented-out code
    |
236 | #                 runtime="vcluster",
237 | #                 health_score=0.95,
238 | #                 logs=[
    | ^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
239 | #                     "Creating shadow environment: demo-api-20260202-120000",
240 | #                     "Host namespace created",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:239:1: ERA001 Found commented-out code
    |
237 | #                 health_score=0.95,
238 | #                 logs=[
239 | #                     "Creating shadow environment: demo-api-20260202-120000",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
240 | #                     "Host namespace created",
241 | #                     "vCluster created",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:244:1: ERA001 Found commented-out code
    |
242 | #                     "Resource cloned into vCluster",
243 | #                 ],
244 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
245 |
246 | #         async def mock_run_verification(*args, **kwargs):
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:247:1: ERA001 Found commented-out code
    |
246 | #         async def mock_run_verification(*args, **kwargs):
247 | #             return True  # Verification passed
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
248 |
249 | #         async def mock_cleanup(*args, **kwargs):
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:252:1: ERA001 Found commented-out code
    |
250 | #             pass
251 |
252 | #         mock_manager.create_shadow = mock_create_shadow
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
253 | #         mock_manager.run_verification = mock_run_verification
254 | #         mock_manager.cleanup = mock_cleanup
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:253:1: ERA001 Found commented-out code
    |
252 | #         mock_manager.create_shadow = mock_create_shadow
253 | #         mock_manager.run_verification = mock_run_verification
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
254 | #         mock_manager.cleanup = mock_cleanup
255 | #         mock_manager.get_environment.return_value = None
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:254:1: ERA001 Found commented-out code
    |
252 | #         mock_manager.create_shadow = mock_create_shadow
253 | #         mock_manager.run_verification = mock_run_verification
254 | #         mock_manager.cleanup = mock_cleanup
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
255 | #         mock_manager.get_environment.return_value = None
256 | #         mock_manager.list_environments.return_value = []
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:255:1: ERA001 Found commented-out code
    |
253 | #         mock_manager.run_verification = mock_run_verification
254 | #         mock_manager.cleanup = mock_cleanup
255 | #         mock_manager.get_environment.return_value = None
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
256 | #         mock_manager.list_environments.return_value = []
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:256:1: ERA001 Found commented-out code
    |
254 | #         mock_manager.cleanup = mock_cleanup
255 | #         mock_manager.get_environment.return_value = None
256 | #         mock_manager.list_environments.return_value = []
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
257 |
258 | #         mock_class.return_value = mock_manager
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:258:1: ERA001 Found commented-out code
    |
256 | #         mock_manager.list_environments.return_value = []
257 |
258 | #         mock_class.return_value = mock_manager
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
259 |
260 | #         with patch("aegis.shadow.manager.get_shadow_manager", return_value=mock_manager):
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:276:1: ERA001 Found commented-out code
    |
274 | #         with patch("subprocess.run") as mock_run:
275 | #             mock_run.return_value = MagicMock(
276 | #                 returncode=0,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
277 | #                 stdout="aegis\nRunning\n",
278 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:277:1: ERA001 Found commented-out code
    |
275 | #             mock_run.return_value = MagicMock(
276 | #                 returncode=0,
277 | #                 stdout="aegis\nRunning\n",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
278 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:278:1: ERA001 Found commented-out code
    |
276 | #                 returncode=0,
277 | #                 stdout="aegis\nRunning\n",
278 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
279 |
280 | #             # The subprocess.run is mocked, so this tests the mock behavior
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:282:1: ERA001 Found commented-out code
    |
280 | #             # The subprocess.run is mocked, so this tests the mock behavior
281 | #             subprocess.run(
282 | #                 ["minikube", "status", "-p", "aegis"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
283 | #                 check=False,
284 | #                 capture_output=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:283:1: ERA001 Found commented-out code
    |
281 | #             subprocess.run(
282 | #                 ["minikube", "status", "-p", "aegis"],
283 | #                 check=False,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
284 | #                 capture_output=True,
285 | #                 text=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:284:1: ERA001 Found commented-out code
    |
282 | #                 ["minikube", "status", "-p", "aegis"],
283 | #                 check=False,
284 | #                 capture_output=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
285 | #                 text=True,
286 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:285:1: ERA001 Found commented-out code
    |
283 | #                 check=False,
284 | #                 capture_output=True,
285 | #                 text=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
286 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:286:1: ERA001 Found commented-out code
    |
284 | #                 capture_output=True,
285 | #                 text=True,
286 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
287 |
288 | #             assert mock_cluster_context.minikube_running
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:289:1: ERA001 Found commented-out code
    |
288 | #             assert mock_cluster_context.minikube_running
289 | #             mock_run.assert_called_once()
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
290 |
291 | #     def test_docker_compose_services_check(self, mock_cluster_context: MockClusterContext) -> None:
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:294:1: ERA001 Found commented-out code
    |
292 | #         """Verify docker compose services are running."""
293 | #         # Expected services that should be running
294 | #         _ = ["prometheus", "grafana", "loki", "promtail"]
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
295 |
296 | #         with patch("subprocess.run") as mock_run:
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:298:1: ERA001 Found commented-out code
    |
296 | #         with patch("subprocess.run") as mock_run:
297 | #             mock_run.return_value = MagicMock(
298 | #                 returncode=0,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
299 | #                 stdout=json.dumps(
300 | #                     [
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:299:1: ERA001 Found commented-out code
    |
297 | #             mock_run.return_value = MagicMock(
298 | #                 returncode=0,
299 | #                 stdout=json.dumps(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
300 | #                     [
301 | #                         {"Name": "aegis-prometheus", "State": "running"},
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:300:1: ERA001 Found commented-out code
    |
298 | #                 returncode=0,
299 | #                 stdout=json.dumps(
300 | #                     [
    | ^^^^^^^^^^^^^^^^^^^^^^^ ERA001
301 | #                         {"Name": "aegis-prometheus", "State": "running"},
302 | #                         {"Name": "aegis-grafana", "State": "running"},
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:301:1: ERA001 Found commented-out code
    |
299 | #                 stdout=json.dumps(
300 | #                     [
301 | #                         {"Name": "aegis-prometheus", "State": "running"},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
302 | #                         {"Name": "aegis-grafana", "State": "running"},
303 | #                         {"Name": "aegis-loki", "State": "running"},
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:302:1: ERA001 Found commented-out code
    |
300 | #                     [
301 | #                         {"Name": "aegis-prometheus", "State": "running"},
302 | #                         {"Name": "aegis-grafana", "State": "running"},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
303 | #                         {"Name": "aegis-loki", "State": "running"},
304 | #                         {"Name": "aegis-promtail", "State": "running"},
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:303:1: ERA001 Found commented-out code
    |
301 | #                         {"Name": "aegis-prometheus", "State": "running"},
302 | #                         {"Name": "aegis-grafana", "State": "running"},
303 | #                         {"Name": "aegis-loki", "State": "running"},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
304 | #                         {"Name": "aegis-promtail", "State": "running"},
305 | #                     ],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:304:1: ERA001 Found commented-out code
    |
302 | #                         {"Name": "aegis-grafana", "State": "running"},
303 | #                         {"Name": "aegis-loki", "State": "running"},
304 | #                         {"Name": "aegis-promtail", "State": "running"},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
305 | #                     ],
306 | #                 ),
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:307:1: ERA001 Found commented-out code
    |
305 | #                     ],
306 | #                 ),
307 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
308 |
309 | #             assert mock_cluster_context.docker_compose_running
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:317:1: ERA001 Found commented-out code
    |
315 | #         """Verify Ollama is available and responding."""
316 | #         with patch("httpx.get") as mock_get:
317 | #             mock_response = MagicMock()
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
318 | #             mock_response.status_code = 200
319 | #             mock_response.json.return_value = {
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:318:1: ERA001 Found commented-out code
    |
316 | #         with patch("httpx.get") as mock_get:
317 | #             mock_response = MagicMock()
318 | #             mock_response.status_code = 200
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
319 | #             mock_response.json.return_value = {
320 | #                 "models": [
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:321:1: ERA001 Found commented-out code
    |
319 | #             mock_response.json.return_value = {
320 | #                 "models": [
321 | #                     {"name": "phi3:mini"},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
322 | #                     {"name": "tinyllama:latest"},
323 | #                 ],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:322:1: ERA001 Found commented-out code
    |
320 | #                 "models": [
321 | #                     {"name": "phi3:mini"},
322 | #                     {"name": "tinyllama:latest"},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
323 | #                 ],
324 | #             }
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:324:1: ERA001 Found commented-out code
    |
322 | #                     {"name": "tinyllama:latest"},
323 | #                 ],
324 | #             }
    | ^^^^^^^^^^^^^^^ ERA001
325 | #             mock_get.return_value = mock_response
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:325:1: ERA001 Found commented-out code
    |
323 | #                 ],
324 | #             }
325 | #             mock_get.return_value = mock_response
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
326 |
327 | #             assert mock_cluster_context.ollama_available
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:332:1: ERA001 Found commented-out code
    |
330 | #         """Verify K8sGPT CLI is installed."""
331 | #         with patch("shutil.which") as mock_which:
332 | #             mock_which.return_value = "/usr/local/bin/k8sgpt"
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
333 |
334 | #             assert mock_cluster_context.k8sgpt_installed
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:339:1: ERA001 Found commented-out code
    |
337 | #         """Verify vCluster CLI is installed."""
338 | #         with patch("shutil.which") as mock_which:
339 | #             mock_which.return_value = "/usr/local/bin/vcluster"
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
340 |
341 | #             assert mock_cluster_context.vcluster_installed
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:360:1: ERA001 Found commented-out code
    |
358 | #         """Test K8sGPT output is correctly fed to RCA agent."""
359 | #         # Analyze an incident with mock data
360 | #         result = await analyze_incident(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
361 | #             resource_type="deployment",
362 | #             resource_name="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:361:1: ERA001 Found commented-out code
    |
359 | #         # Analyze an incident with mock data
360 | #         result = await analyze_incident(
361 | #             resource_type="deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
362 | #             resource_name="demo-api",
363 | #             namespace="default",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:362:1: ERA001 Found commented-out code
    |
360 | #         result = await analyze_incident(
361 | #             resource_type="deployment",
362 | #             resource_name="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
363 | #             namespace="default",
364 | #             use_mock=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:363:1: ERA001 Found commented-out code
    |
361 | #             resource_type="deployment",
362 | #             resource_name="demo-api",
363 | #             namespace="default",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
364 | #             use_mock=True,
365 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:364:1: ERA001 Found commented-out code
    |
362 | #             resource_name="demo-api",
363 | #             namespace="default",
364 | #             use_mock=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
365 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:365:1: ERA001 Found commented-out code
    |
363 | #             namespace="default",
364 | #             use_mock=True,
365 | #         )
    | ^^^^^^^^^^^ ERA001
366 |
367 | #         # Verify K8sGPT analysis was performed
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:368:1: ERA001 Found commented-out code
    |
367 | #         # Verify K8sGPT analysis was performed
368 | #         assert result.get("k8sgpt_analysis") is not None or result.get("k8sgpt_raw") is not None
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
369 |
370 | #         # Verify RCA agent received and processed the data
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:371:1: ERA001 Found commented-out code
    |
370 | #         # Verify RCA agent received and processed the data
371 | #         rca = result.get("rca_result")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
372 | #         assert rca is not None
373 | #         assert rca.root_cause is not None
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:374:1: ERA001 Found commented-out code
    |
372 | #         assert rca is not None
373 | #         assert rca.root_cause is not None
374 | #         assert rca.confidence_score >= 0.0
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
375 | #         assert len(rca.affected_components) > 0
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:375:1: ERA001 Found commented-out code
    |
373 | #         assert rca.root_cause is not None
374 | #         assert rca.confidence_score >= 0.0
375 | #         assert len(rca.affected_components) > 0
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
376 |
377 | #     @pytest.mark.asyncio
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:384:1: ERA001 Found commented-out code
    |
382 | #     ) -> None:
383 | #         """Test RCA output is correctly fed to Solution agent."""
384 | #         result = await analyze_incident(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
385 | #             resource_type="deployment",
386 | #             resource_name="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:385:1: ERA001 Found commented-out code
    |
383 | #         """Test RCA output is correctly fed to Solution agent."""
384 | #         result = await analyze_incident(
385 | #             resource_type="deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
386 | #             resource_name="demo-api",
387 | #             namespace="default",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:386:1: ERA001 Found commented-out code
    |
384 | #         result = await analyze_incident(
385 | #             resource_type="deployment",
386 | #             resource_name="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
387 | #             namespace="default",
388 | #             use_mock=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:387:1: ERA001 Found commented-out code
    |
385 | #             resource_type="deployment",
386 | #             resource_name="demo-api",
387 | #             namespace="default",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
388 | #             use_mock=True,
389 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:388:1: ERA001 Found commented-out code
    |
386 | #             resource_name="demo-api",
387 | #             namespace="default",
388 | #             use_mock=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
389 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:389:1: ERA001 Found commented-out code
    |
387 | #             namespace="default",
388 | #             use_mock=True,
389 | #         )
    | ^^^^^^^^^^^ ERA001
390 |
391 | #         rca = result.get("rca_result")
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:391:1: ERA001 Found commented-out code
    |
389 | #         )
390 |
391 | #         rca = result.get("rca_result")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
392 | #         fix = result.get("fix_proposal")
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:392:1: ERA001 Found commented-out code
    |
391 | #         rca = result.get("rca_result")
392 | #         fix = result.get("fix_proposal")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
393 |
394 | #         # If confidence is high enough, solution should be generated
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:399:1: ERA001 Found commented-out code
    |
397 | #             assert fix.description is not None
398 | #             assert fix.fix_type is not None
399 | #             assert len(fix.commands) > 0 or len(fix.manifests) > 0
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
400 |
401 | #     @pytest.mark.asyncio
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:408:1: ERA001 Found commented-out code
    |
406 | #     ) -> None:
407 | #         """Test Solution output is correctly fed to Verifier agent."""
408 | #         result = await analyze_incident(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
409 | #             resource_type="deployment",
410 | #             resource_name="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:409:1: ERA001 Found commented-out code
    |
407 | #         """Test Solution output is correctly fed to Verifier agent."""
408 | #         result = await analyze_incident(
409 | #             resource_type="deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
410 | #             resource_name="demo-api",
411 | #             namespace="production",  # Production triggers verification
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:410:1: ERA001 Found commented-out code
    |
408 | #         result = await analyze_incident(
409 | #             resource_type="deployment",
410 | #             resource_name="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
411 | #             namespace="production",  # Production triggers verification
412 | #             use_mock=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:411:1: ERA001 Found commented-out code
    |
409 | #             resource_type="deployment",
410 | #             resource_name="demo-api",
411 | #             namespace="production",  # Production triggers verification
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
412 | #             use_mock=True,
413 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:412:1: ERA001 Found commented-out code
    |
410 | #             resource_name="demo-api",
411 | #             namespace="production",  # Production triggers verification
412 | #             use_mock=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
413 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:413:1: ERA001 Found commented-out code
    |
411 | #             namespace="production",  # Production triggers verification
412 | #             use_mock=True,
413 | #         )
    | ^^^^^^^^^^^ ERA001
414 |
415 | #         fix = result.get("fix_proposal")
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:415:1: ERA001 Found commented-out code
    |
413 | #         )
414 |
415 | #         fix = result.get("fix_proposal")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
416 | #         _ = result.get("verification_plan")  # May be generated for high-risk fixes
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:416:1: ERA001 Found commented-out code
    |
415 | #         fix = result.get("fix_proposal")
416 | #         _ = result.get("verification_plan")  # May be generated for high-risk fixes
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
417 |
418 | #         # For high-risk or production, verification should be generated
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:429:1: ERA001 Found commented-out code
    |
427 | #         mock_k8sgpt_analyzer,
428 | #     ) -> None:
429 | #         """Test complete agent chain: K8sGPT → RCA → Solution → Verifier."""
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
430 | #         result = await analyze_incident(
431 | #             resource_type="deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:430:1: ERA001 Found commented-out code
    |
428 | #     ) -> None:
429 | #         """Test complete agent chain: K8sGPT → RCA → Solution → Verifier."""
430 | #         result = await analyze_incident(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
431 | #             resource_type="deployment",
432 | #             resource_name="api-server",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:431:1: ERA001 Found commented-out code
    |
429 | #         """Test complete agent chain: K8sGPT → RCA → Solution → Verifier."""
430 | #         result = await analyze_incident(
431 | #             resource_type="deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
432 | #             resource_name="api-server",
433 | #             namespace="production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:432:1: ERA001 Found commented-out code
    |
430 | #         result = await analyze_incident(
431 | #             resource_type="deployment",
432 | #             resource_name="api-server",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
433 | #             namespace="production",
434 | #             use_mock=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:433:1: ERA001 Found commented-out code
    |
431 | #             resource_type="deployment",
432 | #             resource_name="api-server",
433 | #             namespace="production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
434 | #             use_mock=True,
435 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:434:1: ERA001 Found commented-out code
    |
432 | #             resource_name="api-server",
433 | #             namespace="production",
434 | #             use_mock=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
435 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:435:1: ERA001 Found commented-out code
    |
433 | #             namespace="production",
434 | #             use_mock=True,
435 | #         )
    | ^^^^^^^^^^^ ERA001
436 |
437 | #         # Verify workflow completed
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:441:1: ERA001 Found commented-out code
    |
440 | #         # Verify RCA ran
441 | #         assert result.get("rca_result") is not None
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
442 |
443 | #         # Verify no fatal errors (low confidence is OK)
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:444:1: ERA001 Found commented-out code
    |
443 | #         # Verify no fatal errors (low confidence is OK)
444 | #         error = result.get("error")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
445 | #         if error:
446 | #             # Error should only be for low confidence, not crash
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:447:1: ERA001 Found commented-out code
    |
445 | #         if error:
446 | #             # Error should only be for low confidence, not crash
447 | #             assert "confidence" in error.lower() or error is None
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:464:1: ERA001 Found commented-out code
    |
462 | #     ) -> None:
463 | #         """Test shadow environment is created correctly."""
464 | #         env = await mock_shadow_manager.create_shadow(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
465 | #             source_namespace="default",
466 | #             source_resource="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:465:1: ERA001 Found commented-out code
    |
463 | #         """Test shadow environment is created correctly."""
464 | #         env = await mock_shadow_manager.create_shadow(
465 | #             source_namespace="default",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
466 | #             source_resource="demo-api",
467 | #             source_resource_kind="Deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:466:1: ERA001 Found commented-out code
    |
464 | #         env = await mock_shadow_manager.create_shadow(
465 | #             source_namespace="default",
466 | #             source_resource="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
467 | #             source_resource_kind="Deployment",
468 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:467:1: ERA001 Found commented-out code
    |
465 | #             source_namespace="default",
466 | #             source_resource="demo-api",
467 | #             source_resource_kind="Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
468 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:468:1: ERA001 Found commented-out code
    |
466 | #             source_resource="demo-api",
467 | #             source_resource_kind="Deployment",
468 | #         )
    | ^^^^^^^^^^^ ERA001
469 |
470 | #         assert env is not None
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:472:1: ERA001 Found commented-out code
    |
470 | #         assert env is not None
471 | #         assert env.id is not None
472 | #         assert env.runtime == "vcluster"
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
473 | #         assert len(env.logs) > 0
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:473:1: ERA001 Found commented-out code
    |
471 | #         assert env.id is not None
472 | #         assert env.runtime == "vcluster"
473 | #         assert len(env.logs) > 0
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
474 |
475 | #     @pytest.mark.asyncio
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:481:1: ERA001 Found commented-out code
    |
479 | #     ) -> None:
480 | #         """Test fix is verified in shadow environment."""
481 | #         env = await mock_shadow_manager.create_shadow(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
482 | #             source_namespace="default",
483 | #             source_resource="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:482:1: ERA001 Found commented-out code
    |
480 | #         """Test fix is verified in shadow environment."""
481 | #         env = await mock_shadow_manager.create_shadow(
482 | #             source_namespace="default",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
483 | #             source_resource="demo-api",
484 | #             source_resource_kind="Deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:483:1: ERA001 Found commented-out code
    |
481 | #         env = await mock_shadow_manager.create_shadow(
482 | #             source_namespace="default",
483 | #             source_resource="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
484 | #             source_resource_kind="Deployment",
485 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:484:1: ERA001 Found commented-out code
    |
482 | #             source_namespace="default",
483 | #             source_resource="demo-api",
484 | #             source_resource_kind="Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
485 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:485:1: ERA001 Found commented-out code
    |
483 | #             source_resource="demo-api",
484 | #             source_resource_kind="Deployment",
485 | #         )
    | ^^^^^^^^^^^ ERA001
486 |
487 | #         # Apply fix changes in shadow
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:488:1: ERA001 Found commented-out code
    |
487 | #         # Apply fix changes in shadow
488 | #         changes = {
    | ^^^^^^^^^^^^^^^^^^^^^ ERA001
489 | #             "resources": {"limits": {"memory": "512Mi"}},
490 | #         }
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:489:1: ERA001 Found commented-out code
    |
487 | #         # Apply fix changes in shadow
488 | #         changes = {
489 | #             "resources": {"limits": {"memory": "512Mi"}},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
490 | #         }
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:490:1: ERA001 Found commented-out code
    |
488 | #         changes = {
489 | #             "resources": {"limits": {"memory": "512Mi"}},
490 | #         }
    | ^^^^^^^^^^^ ERA001
491 |
492 | #         passed = await mock_shadow_manager.run_verification(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:492:1: ERA001 Found commented-out code
    |
490 | #         }
491 |
492 | #         passed = await mock_shadow_manager.run_verification(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
493 | #             shadow_id=env.id,
494 | #             changes=changes,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:493:1: ERA001 Found commented-out code
    |
492 | #         passed = await mock_shadow_manager.run_verification(
493 | #             shadow_id=env.id,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
494 | #             changes=changes,
495 | #             duration=60,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:494:1: ERA001 Found commented-out code
    |
492 | #         passed = await mock_shadow_manager.run_verification(
493 | #             shadow_id=env.id,
494 | #             changes=changes,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
495 | #             duration=60,
496 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:495:1: ERA001 Found commented-out code
    |
493 | #             shadow_id=env.id,
494 | #             changes=changes,
495 | #             duration=60,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
496 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:496:1: ERA001 Found commented-out code
    |
494 | #             changes=changes,
495 | #             duration=60,
496 | #         )
    | ^^^^^^^^^^^ ERA001
497 |
498 | #         assert passed is True
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:506:1: ERA001 Found commented-out code
    |
504 | #     ) -> None:
505 | #         """Test shadow environment cleanup."""
506 | #         env = await mock_shadow_manager.create_shadow(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
507 | #             source_namespace="default",
508 | #             source_resource="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:507:1: ERA001 Found commented-out code
    |
505 | #         """Test shadow environment cleanup."""
506 | #         env = await mock_shadow_manager.create_shadow(
507 | #             source_namespace="default",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
508 | #             source_resource="demo-api",
509 | #             source_resource_kind="Deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:508:1: ERA001 Found commented-out code
    |
506 | #         env = await mock_shadow_manager.create_shadow(
507 | #             source_namespace="default",
508 | #             source_resource="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
509 | #             source_resource_kind="Deployment",
510 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:509:1: ERA001 Found commented-out code
    |
507 | #             source_namespace="default",
508 | #             source_resource="demo-api",
509 | #             source_resource_kind="Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
510 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:510:1: ERA001 Found commented-out code
    |
508 | #             source_resource="demo-api",
509 | #             source_resource_kind="Deployment",
510 | #         )
    | ^^^^^^^^^^^ ERA001
511 |
512 | #         await mock_shadow_manager.cleanup(env.id)
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:512:1: ERA001 Found commented-out code
    |
510 | #         )
511 |
512 | #         await mock_shadow_manager.cleanup(env.id)
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
513 |
514 | #         # Cleanup called successfully
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:529:1: ERA001 Found commented-out code
    |
527 | #         """Test user confirms to apply fix to production."""
528 | #         with patch("typer.confirm") as mock_confirm:
529 | #             mock_confirm.return_value = True
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
530 |
531 | #             # Simulate confirmation
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:532:1: ERA001 Found commented-out code
    |
531 | #             # Simulate confirmation
532 | #             result = mock_confirm("Apply fix to production cluster?")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
533 |
534 | #             assert result is True
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:535:1: ERA001 Found commented-out code
    |
534 | #             assert result is True
535 | #             mock_confirm.assert_called_once()
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
536 |
537 | #     def test_user_rejects_fix_application(self) -> None:
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:540:1: ERA001 Found commented-out code
    |
538 | #         """Test user rejects fix application."""
539 | #         with patch("typer.confirm") as mock_confirm:
540 | #             mock_confirm.return_value = False
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
541 |
542 | #             # Simulate rejection
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:543:1: ERA001 Found commented-out code
    |
542 | #             # Simulate rejection
543 | #             result = mock_confirm("Apply fix to production cluster?")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
544 |
545 | #             assert result is False
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:549:1: ERA001 Found commented-out code
    |
547 | #     def test_abort_generates_report(self) -> None:
548 | #         """Test aborting generates a proper report."""
549 | #         report_data = {
    | ^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
550 | #             "timestamp": datetime.now(UTC).isoformat(),
551 | #             "decision": "aborted",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:550:1: ERA001 Found commented-out code
    |
548 | #         """Test aborting generates a proper report."""
549 | #         report_data = {
550 | #             "timestamp": datetime.now(UTC).isoformat(),
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
551 | #             "decision": "aborted",
552 | #             "reason": "User declined to apply fix",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:551:1: ERA001 Found commented-out code
    |
549 | #         report_data = {
550 | #             "timestamp": datetime.now(UTC).isoformat(),
551 | #             "decision": "aborted",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
552 | #             "reason": "User declined to apply fix",
553 | #             "resource": "deployment/demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:552:1: ERA001 Found commented-out code
    |
550 | #             "timestamp": datetime.now(UTC).isoformat(),
551 | #             "decision": "aborted",
552 | #             "reason": "User declined to apply fix",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
553 | #             "resource": "deployment/demo-api",
554 | #             "namespace": "production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:553:1: ERA001 Found commented-out code
    |
551 | #             "decision": "aborted",
552 | #             "reason": "User declined to apply fix",
553 | #             "resource": "deployment/demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
554 | #             "namespace": "production",
555 | #             "rca_summary": "Container OOMKilled due to memory exhaustion",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:554:1: ERA001 Found commented-out code
    |
552 | #             "reason": "User declined to apply fix",
553 | #             "resource": "deployment/demo-api",
554 | #             "namespace": "production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
555 | #             "rca_summary": "Container OOMKilled due to memory exhaustion",
556 | #             "proposed_fix": "Increase memory limit to 512Mi",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:555:1: ERA001 Found commented-out code
    |
553 | #             "resource": "deployment/demo-api",
554 | #             "namespace": "production",
555 | #             "rca_summary": "Container OOMKilled due to memory exhaustion",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
556 | #             "proposed_fix": "Increase memory limit to 512Mi",
557 | #             "shadow_verification": {
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:556:1: ERA001 Found commented-out code
    |
554 | #             "namespace": "production",
555 | #             "rca_summary": "Container OOMKilled due to memory exhaustion",
556 | #             "proposed_fix": "Increase memory limit to 512Mi",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
557 | #             "shadow_verification": {
558 | #                 "passed": True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:557:1: ERA001 Found commented-out code
    |
555 | #             "rca_summary": "Container OOMKilled due to memory exhaustion",
556 | #             "proposed_fix": "Increase memory limit to 512Mi",
557 | #             "shadow_verification": {
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
558 | #                 "passed": True,
559 | #                 "health_score": 0.95,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:558:1: ERA001 Found commented-out code
    |
556 | #             "proposed_fix": "Increase memory limit to 512Mi",
557 | #             "shadow_verification": {
558 | #                 "passed": True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
559 | #                 "health_score": 0.95,
560 | #             },
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:559:1: ERA001 Found commented-out code
    |
557 | #             "shadow_verification": {
558 | #                 "passed": True,
559 | #                 "health_score": 0.95,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
560 | #             },
561 | #         }
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:561:1: ERA001 Found commented-out code
    |
559 | #                 "health_score": 0.95,
560 | #             },
561 | #         }
    | ^^^^^^^^^^^ ERA001
562 |
563 | #         assert report_data["decision"] == "aborted"
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:563:1: ERA001 Found commented-out code
    |
561 | #         }
562 |
563 | #         assert report_data["decision"] == "aborted"
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
564 | #         assert "shadow_verification" in report_data
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:578:1: ERA001 Found commented-out code
    |
576 | #     async def test_fix_application_with_dry_run(self, mock_k8s_client) -> None:
577 | #         """Test fix is applied with dry-run validation."""
578 | #         from aegis.kubernetes.fix_applier import FixApplier
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
579 |
580 | #         _ = mock_k8s_client["apps"]  # Acknowledge we have access to apps client
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:580:1: ERA001 Found commented-out code
    |
578 | #         from aegis.kubernetes.fix_applier import FixApplier
579 |
580 | #         _ = mock_k8s_client["apps"]  # Acknowledge we have access to apps client
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
581 |
582 | #         applier = FixApplier()
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:582:1: ERA001 Found commented-out code
    |
580 | #         _ = mock_k8s_client["apps"]  # Acknowledge we have access to apps client
581 |
582 | #         applier = FixApplier()
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
583 |
584 | #         fix_proposal = CRDFixProposal(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:584:1: ERA001 Found commented-out code
    |
582 | #         applier = FixApplier()
583 |
584 | #         fix_proposal = CRDFixProposal(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
585 | #             fixType=CRDFixType.RESTART,
586 | #             description="Restart deployment to apply new configuration",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:585:1: ERA001 Found commented-out code
    |
584 | #         fix_proposal = CRDFixProposal(
585 | #             fixType=CRDFixType.RESTART,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
586 | #             description="Restart deployment to apply new configuration",
587 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:586:1: ERA001 Found commented-out code
    |
584 | #         fix_proposal = CRDFixProposal(
585 | #             fixType=CRDFixType.RESTART,
586 | #             description="Restart deployment to apply new configuration",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
587 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:587:1: ERA001 Found commented-out code
    |
585 | #             fixType=CRDFixType.RESTART,
586 | #             description="Restart deployment to apply new configuration",
587 | #         )
    | ^^^^^^^^^^^ ERA001
588 |
589 | #         result = await applier.apply_fix(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:589:1: ERA001 Found commented-out code
    |
587 | #         )
588 |
589 | #         result = await applier.apply_fix(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
590 | #             fix_proposal=fix_proposal,
591 | #             resource_kind="Deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:590:1: ERA001 Found commented-out code
    |
589 | #         result = await applier.apply_fix(
590 | #             fix_proposal=fix_proposal,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
591 | #             resource_kind="Deployment",
592 | #             resource_name="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:591:1: ERA001 Found commented-out code
    |
589 | #         result = await applier.apply_fix(
590 | #             fix_proposal=fix_proposal,
591 | #             resource_kind="Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
592 | #             resource_name="demo-api",
593 | #             namespace="production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:592:1: ERA001 Found commented-out code
    |
590 | #             fix_proposal=fix_proposal,
591 | #             resource_kind="Deployment",
592 | #             resource_name="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
593 | #             namespace="production",
594 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:593:1: ERA001 Found commented-out code
    |
591 | #             resource_kind="Deployment",
592 | #             resource_name="demo-api",
593 | #             namespace="production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
594 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:594:1: ERA001 Found commented-out code
    |
592 | #             resource_name="demo-api",
593 | #             namespace="production",
594 | #         )
    | ^^^^^^^^^^^ ERA001
595 |
596 | #         assert result.success is True
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:603:1: ERA001 Found commented-out code
    |
601 | #     async def test_fix_application_records_rollback_info(self, mock_k8s_client) -> None:
602 | #         """Test rollback information is recorded during fix application."""
603 | #         from aegis.kubernetes.fix_applier import FixApplier
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
604 |
605 | #         _ = mock_k8s_client  # Acknowledge fixture is loaded
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:605:1: ERA001 Found commented-out code
    |
603 | #         from aegis.kubernetes.fix_applier import FixApplier
604 |
605 | #         _ = mock_k8s_client  # Acknowledge fixture is loaded
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
606 |
607 | #         applier = FixApplier()
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:607:1: ERA001 Found commented-out code
    |
605 | #         _ = mock_k8s_client  # Acknowledge fixture is loaded
606 |
607 | #         applier = FixApplier()
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
608 |
609 | #         fix_proposal = CRDFixProposal(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:609:1: ERA001 Found commented-out code
    |
607 | #         applier = FixApplier()
608 |
609 | #         fix_proposal = CRDFixProposal(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
610 | #             fixType=CRDFixType.RESTART,
611 | #             description="Restart deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:610:1: ERA001 Found commented-out code
    |
609 | #         fix_proposal = CRDFixProposal(
610 | #             fixType=CRDFixType.RESTART,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
611 | #             description="Restart deployment",
612 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:611:1: ERA001 Found commented-out code
    |
609 | #         fix_proposal = CRDFixProposal(
610 | #             fixType=CRDFixType.RESTART,
611 | #             description="Restart deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
612 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:612:1: ERA001 Found commented-out code
    |
610 | #             fixType=CRDFixType.RESTART,
611 | #             description="Restart deployment",
612 | #         )
    | ^^^^^^^^^^^ ERA001
613 |
614 | #         result = await applier.apply_fix(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:614:1: ERA001 Found commented-out code
    |
612 | #         )
613 |
614 | #         result = await applier.apply_fix(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
615 | #             fix_proposal=fix_proposal,
616 | #             resource_kind="Deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:615:1: ERA001 Found commented-out code
    |
614 | #         result = await applier.apply_fix(
615 | #             fix_proposal=fix_proposal,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
616 | #             resource_kind="Deployment",
617 | #             resource_name="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:616:1: ERA001 Found commented-out code
    |
614 | #         result = await applier.apply_fix(
615 | #             fix_proposal=fix_proposal,
616 | #             resource_kind="Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
617 | #             resource_name="demo-api",
618 | #             namespace="production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:617:1: ERA001 Found commented-out code
    |
615 | #             fix_proposal=fix_proposal,
616 | #             resource_kind="Deployment",
617 | #             resource_name="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
618 | #             namespace="production",
619 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:618:1: ERA001 Found commented-out code
    |
616 | #             resource_kind="Deployment",
617 | #             resource_name="demo-api",
618 | #             namespace="production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
619 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:619:1: ERA001 Found commented-out code
    |
617 | #             resource_name="demo-api",
618 | #             namespace="production",
619 | #         )
    | ^^^^^^^^^^^ ERA001
620 |
621 | #         assert result.rollback_info is not None
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:638:1: ERA001 Found commented-out code
    |
636 | #         """Convert agent FixProposal to CRD FixProposal for fix_applier."""
637 | #         return CRDFixProposal(
638 | #             fixType=CRDFixType(agent_fix.fix_type.value),
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
639 | #             description=agent_fix.description,
640 | #             commands=agent_fix.commands,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:639:1: ERA001 Found commented-out code
    |
637 | #         return CRDFixProposal(
638 | #             fixType=CRDFixType(agent_fix.fix_type.value),
639 | #             description=agent_fix.description,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
640 | #             commands=agent_fix.commands,
641 | #             manifests=agent_fix.manifests,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:640:1: ERA001 Found commented-out code
    |
638 | #             fixType=CRDFixType(agent_fix.fix_type.value),
639 | #             description=agent_fix.description,
640 | #             commands=agent_fix.commands,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
641 | #             manifests=agent_fix.manifests,
642 | #             confidenceScore=agent_fix.confidence_score,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:641:1: ERA001 Found commented-out code
    |
639 | #             description=agent_fix.description,
640 | #             commands=agent_fix.commands,
641 | #             manifests=agent_fix.manifests,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
642 | #             confidenceScore=agent_fix.confidence_score,
643 | #             estimatedDowntime=agent_fix.estimated_downtime,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:642:1: ERA001 Found commented-out code
    |
640 | #             commands=agent_fix.commands,
641 | #             manifests=agent_fix.manifests,
642 | #             confidenceScore=agent_fix.confidence_score,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
643 | #             estimatedDowntime=agent_fix.estimated_downtime,
644 | #             risks=agent_fix.risks,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:643:1: ERA001 Found commented-out code
    |
641 | #             manifests=agent_fix.manifests,
642 | #             confidenceScore=agent_fix.confidence_score,
643 | #             estimatedDowntime=agent_fix.estimated_downtime,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
644 | #             risks=agent_fix.risks,
645 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:644:1: ERA001 Found commented-out code
    |
642 | #             confidenceScore=agent_fix.confidence_score,
643 | #             estimatedDowntime=agent_fix.estimated_downtime,
644 | #             risks=agent_fix.risks,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
645 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:645:1: ERA001 Found commented-out code
    |
643 | #             estimatedDowntime=agent_fix.estimated_downtime,
644 | #             risks=agent_fix.risks,
645 | #         )
    | ^^^^^^^^^^^ ERA001
646 |
647 | #     @pytest.mark.asyncio
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:657:1: ERA001 Found commented-out code
    |
655 | #         """Test complete workflow from incident detection to fix application."""
656 | #         # Step 1: Analyze incident (K8sGPT → RCA → Solution → Verifier)
657 | #         result = await analyze_incident(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
658 | #             resource_type="deployment",
659 | #             resource_name="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:658:1: ERA001 Found commented-out code
    |
656 | #         # Step 1: Analyze incident (K8sGPT → RCA → Solution → Verifier)
657 | #         result = await analyze_incident(
658 | #             resource_type="deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
659 | #             resource_name="demo-api",
660 | #             namespace="production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:659:1: ERA001 Found commented-out code
    |
657 | #         result = await analyze_incident(
658 | #             resource_type="deployment",
659 | #             resource_name="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
660 | #             namespace="production",
661 | #             use_mock=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:660:1: ERA001 Found commented-out code
    |
658 | #             resource_type="deployment",
659 | #             resource_name="demo-api",
660 | #             namespace="production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
661 | #             use_mock=True,
662 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:661:1: ERA001 Found commented-out code
    |
659 | #             resource_name="demo-api",
660 | #             namespace="production",
661 | #             use_mock=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
662 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:662:1: ERA001 Found commented-out code
    |
660 | #             namespace="production",
661 | #             use_mock=True,
662 | #         )
    | ^^^^^^^^^^^ ERA001
663 |
664 | #         assert result.get("rca_result") is not None
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:664:1: ERA001 Found commented-out code
    |
662 | #         )
663 |
664 | #         assert result.get("rca_result") is not None
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
665 |
666 | #         # Get workflow results
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:667:1: ERA001 Found commented-out code
    |
666 | #         # Get workflow results
667 | #         _ = result["rca_result"]  # RCA result available
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
668 | #         fix = result.get("fix_proposal")
669 | #         verify = result.get("verification_plan")
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:668:1: ERA001 Found commented-out code
    |
666 | #         # Get workflow results
667 | #         _ = result["rca_result"]  # RCA result available
668 | #         fix = result.get("fix_proposal")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
669 | #         verify = result.get("verification_plan")
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:669:1: ERA001 Found commented-out code
    |
667 | #         _ = result["rca_result"]  # RCA result available
668 | #         fix = result.get("fix_proposal")
669 | #         verify = result.get("verification_plan")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
670 |
671 | #         # Step 2: Create shadow environment (if fix available)
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:673:1: ERA001 Found commented-out code
    |
671 | #         # Step 2: Create shadow environment (if fix available)
672 | #         if fix:
673 | #             env = await mock_shadow_manager.create_shadow(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
674 | #                 source_namespace="production",
675 | #                 source_resource="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:674:1: ERA001 Found commented-out code
    |
672 | #         if fix:
673 | #             env = await mock_shadow_manager.create_shadow(
674 | #                 source_namespace="production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
675 | #                 source_resource="demo-api",
676 | #                 source_resource_kind="Deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:675:1: ERA001 Found commented-out code
    |
673 | #             env = await mock_shadow_manager.create_shadow(
674 | #                 source_namespace="production",
675 | #                 source_resource="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
676 | #                 source_resource_kind="Deployment",
677 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:676:1: ERA001 Found commented-out code
    |
674 | #                 source_namespace="production",
675 | #                 source_resource="demo-api",
676 | #                 source_resource_kind="Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
677 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:677:1: ERA001 Found commented-out code
    |
675 | #                 source_resource="demo-api",
676 | #                 source_resource_kind="Deployment",
677 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
678 |
679 | #             # Step 3: Run shadow verification
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:680:1: ERA001 Found commented-out code
    |
679 | #             # Step 3: Run shadow verification
680 | #             passed = await mock_shadow_manager.run_verification(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
681 | #                 shadow_id=env.id,
682 | #                 changes={"resources": fix.manifests if fix.manifests else {}},
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:681:1: ERA001 Found commented-out code
    |
679 | #             # Step 3: Run shadow verification
680 | #             passed = await mock_shadow_manager.run_verification(
681 | #                 shadow_id=env.id,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
682 | #                 changes={"resources": fix.manifests if fix.manifests else {}},
683 | #                 duration=verify.duration if verify else 60,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:682:1: ERA001 Found commented-out code
    |
680 | #             passed = await mock_shadow_manager.run_verification(
681 | #                 shadow_id=env.id,
682 | #                 changes={"resources": fix.manifests if fix.manifests else {}},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
683 | #                 duration=verify.duration if verify else 60,
684 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:683:1: ERA001 Found commented-out code
    |
681 | #                 shadow_id=env.id,
682 | #                 changes={"resources": fix.manifests if fix.manifests else {}},
683 | #                 duration=verify.duration if verify else 60,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
684 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:684:1: ERA001 Found commented-out code
    |
682 | #                 changes={"resources": fix.manifests if fix.manifests else {}},
683 | #                 duration=verify.duration if verify else 60,
684 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
685 |
686 | #             assert passed is True
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:690:1: ERA001 Found commented-out code
    |
688 | #             # Step 4: User confirmation (mocked as True)
689 | #             with patch("typer.confirm", return_value=True):
690 | #                 user_confirmed = True  # In real CLI this comes from typer.confirm
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
691 |
692 | #                 if user_confirmed:
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:694:1: ERA001 Found commented-out code
    |
692 | #                 if user_confirmed:
693 | #                     # Step 5: Apply fix to production
694 | #                     from aegis.kubernetes.fix_applier import FixApplier
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
695 |
696 | #                     applier = FixApplier()
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:696:1: ERA001 Found commented-out code
    |
694 | #                     from aegis.kubernetes.fix_applier import FixApplier
695 |
696 | #                     applier = FixApplier()
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
697 | #                     crd_fix = self._convert_to_crd_fix_proposal(fix)
698 | #                     apply_result = await applier.apply_fix(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:697:1: ERA001 Found commented-out code
    |
696 | #                     applier = FixApplier()
697 | #                     crd_fix = self._convert_to_crd_fix_proposal(fix)
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
698 | #                     apply_result = await applier.apply_fix(
699 | #                         fix_proposal=crd_fix,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:698:1: ERA001 Found commented-out code
    |
696 | #                     applier = FixApplier()
697 | #                     crd_fix = self._convert_to_crd_fix_proposal(fix)
698 | #                     apply_result = await applier.apply_fix(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
699 | #                         fix_proposal=crd_fix,
700 | #                         resource_kind="Deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:699:1: ERA001 Found commented-out code
    |
697 | #                     crd_fix = self._convert_to_crd_fix_proposal(fix)
698 | #                     apply_result = await applier.apply_fix(
699 | #                         fix_proposal=crd_fix,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
700 | #                         resource_kind="Deployment",
701 | #                         resource_name="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:700:1: ERA001 Found commented-out code
    |
698 | #                     apply_result = await applier.apply_fix(
699 | #                         fix_proposal=crd_fix,
700 | #                         resource_kind="Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
701 | #                         resource_name="demo-api",
702 | #                         namespace="production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:701:1: ERA001 Found commented-out code
    |
699 | #                         fix_proposal=crd_fix,
700 | #                         resource_kind="Deployment",
701 | #                         resource_name="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
702 | #                         namespace="production",
703 | #                     )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:702:1: ERA001 Found commented-out code
    |
700 | #                         resource_kind="Deployment",
701 | #                         resource_name="demo-api",
702 | #                         namespace="production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
703 | #                     )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:703:1: ERA001 Found commented-out code
    |
701 | #                         resource_name="demo-api",
702 | #                         namespace="production",
703 | #                     )
    | ^^^^^^^^^^^^^^^^^^^^^^^ ERA001
704 |
705 | #                     assert apply_result.success is True
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:709:1: ERA001 Found commented-out code
    |
708 | #             # Step 6: Cleanup shadow
709 | #             await mock_shadow_manager.cleanup(env.id)
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
710 |
711 | #     @pytest.mark.asyncio
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:720:1: ERA001 Found commented-out code
    |
718 | #         """Test workflow abort generates comprehensive report."""
719 | #         # Step 1: Analyze incident
720 | #         result = await analyze_incident(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
721 | #             resource_type="deployment",
722 | #             resource_name="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:721:1: ERA001 Found commented-out code
    |
719 | #         # Step 1: Analyze incident
720 | #         result = await analyze_incident(
721 | #             resource_type="deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
722 | #             resource_name="demo-api",
723 | #             namespace="production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:722:1: ERA001 Found commented-out code
    |
720 | #         result = await analyze_incident(
721 | #             resource_type="deployment",
722 | #             resource_name="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
723 | #             namespace="production",
724 | #             use_mock=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:723:1: ERA001 Found commented-out code
    |
721 | #             resource_type="deployment",
722 | #             resource_name="demo-api",
723 | #             namespace="production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
724 | #             use_mock=True,
725 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:724:1: ERA001 Found commented-out code
    |
722 | #             resource_name="demo-api",
723 | #             namespace="production",
724 | #             use_mock=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
725 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:725:1: ERA001 Found commented-out code
    |
723 | #             namespace="production",
724 | #             use_mock=True,
725 | #         )
    | ^^^^^^^^^^^ ERA001
726 |
727 | #         rca = result.get("rca_result")
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:727:1: ERA001 Found commented-out code
    |
725 | #         )
726 |
727 | #         rca = result.get("rca_result")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
728 | #         fix = result.get("fix_proposal")
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:728:1: ERA001 Found commented-out code
    |
727 | #         rca = result.get("rca_result")
728 | #         fix = result.get("fix_proposal")
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
729 |
730 | #         if fix:
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:732:1: ERA001 Found commented-out code
    |
730 | #         if fix:
731 | #             # Step 2: Shadow verification
732 | #             env = await mock_shadow_manager.create_shadow(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
733 | #                 source_namespace="production",
734 | #                 source_resource="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:733:1: ERA001 Found commented-out code
    |
731 | #             # Step 2: Shadow verification
732 | #             env = await mock_shadow_manager.create_shadow(
733 | #                 source_namespace="production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
734 | #                 source_resource="demo-api",
735 | #                 source_resource_kind="Deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:734:1: ERA001 Found commented-out code
    |
732 | #             env = await mock_shadow_manager.create_shadow(
733 | #                 source_namespace="production",
734 | #                 source_resource="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
735 | #                 source_resource_kind="Deployment",
736 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:735:1: ERA001 Found commented-out code
    |
733 | #                 source_namespace="production",
734 | #                 source_resource="demo-api",
735 | #                 source_resource_kind="Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
736 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:736:1: ERA001 Found commented-out code
    |
734 | #                 source_resource="demo-api",
735 | #                 source_resource_kind="Deployment",
736 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
737 |
738 | #             passed = await mock_shadow_manager.run_verification(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:738:1: ERA001 Found commented-out code
    |
736 | #             )
737 |
738 | #             passed = await mock_shadow_manager.run_verification(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
739 | #                 shadow_id=env.id,
740 | #                 changes={},
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:739:1: ERA001 Found commented-out code
    |
738 | #             passed = await mock_shadow_manager.run_verification(
739 | #                 shadow_id=env.id,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
740 | #                 changes={},
741 | #                 duration=60,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:740:1: ERA001 Found commented-out code
    |
738 | #             passed = await mock_shadow_manager.run_verification(
739 | #                 shadow_id=env.id,
740 | #                 changes={},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
741 | #                 duration=60,
742 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:741:1: ERA001 Found commented-out code
    |
739 | #                 shadow_id=env.id,
740 | #                 changes={},
741 | #                 duration=60,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
742 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:742:1: ERA001 Found commented-out code
    |
740 | #                 changes={},
741 | #                 duration=60,
742 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
743 |
744 | #             # Step 3: User declines
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:746:1: ERA001 Found commented-out code
    |
744 | #             # Step 3: User declines
745 | #             with patch("typer.confirm", return_value=False):
746 | #                 user_confirmed = False
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
747 |
748 | #                 if not user_confirmed:
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:750:1: ERA001 Found commented-out code
    |
748 | #                 if not user_confirmed:
749 | #                     # Generate abort report
750 | #                     report = {
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
751 | #                         "timestamp": datetime.now(UTC).isoformat(),
752 | #                         "decision": "aborted",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:751:1: ERA001 Found commented-out code
    |
749 | #                     # Generate abort report
750 | #                     report = {
751 | #                         "timestamp": datetime.now(UTC).isoformat(),
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
752 | #                         "decision": "aborted",
753 | #                         "reason": "User declined to apply fix to production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:752:1: ERA001 Found commented-out code
    |
750 | #                     report = {
751 | #                         "timestamp": datetime.now(UTC).isoformat(),
752 | #                         "decision": "aborted",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
753 | #                         "reason": "User declined to apply fix to production",
754 | #                         "resource": {
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:753:1: ERA001 Found commented-out code
    |
751 | #                         "timestamp": datetime.now(UTC).isoformat(),
752 | #                         "decision": "aborted",
753 | #                         "reason": "User declined to apply fix to production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
754 | #                         "resource": {
755 | #                             "kind": "Deployment",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:754:1: ERA001 Found commented-out code
    |
752 | #                         "decision": "aborted",
753 | #                         "reason": "User declined to apply fix to production",
754 | #                         "resource": {
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
755 | #                             "kind": "Deployment",
756 | #                             "name": "demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:755:1: ERA001 Found commented-out code
    |
753 | #                         "reason": "User declined to apply fix to production",
754 | #                         "resource": {
755 | #                             "kind": "Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
756 | #                             "name": "demo-api",
757 | #                             "namespace": "production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:756:1: ERA001 Found commented-out code
    |
754 | #                         "resource": {
755 | #                             "kind": "Deployment",
756 | #                             "name": "demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
757 | #                             "namespace": "production",
758 | #                         },
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:757:1: ERA001 Found commented-out code
    |
755 | #                             "kind": "Deployment",
756 | #                             "name": "demo-api",
757 | #                             "namespace": "production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
758 | #                         },
759 | #                         "analysis": {
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:759:1: ERA001 Found commented-out code
    |
757 | #                             "namespace": "production",
758 | #                         },
759 | #                         "analysis": {
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
760 | #                             "root_cause": rca.root_cause if rca else None,
761 | #                             "severity": rca.severity.value if rca else None,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:760:1: ERA001 Found commented-out code
    |
758 | #                         },
759 | #                         "analysis": {
760 | #                             "root_cause": rca.root_cause if rca else None,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
761 | #                             "severity": rca.severity.value if rca else None,
762 | #                             "confidence": rca.confidence_score if rca else None,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:761:1: ERA001 Found commented-out code
    |
759 | #                         "analysis": {
760 | #                             "root_cause": rca.root_cause if rca else None,
761 | #                             "severity": rca.severity.value if rca else None,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
762 | #                             "confidence": rca.confidence_score if rca else None,
763 | #                         },
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:762:1: ERA001 Found commented-out code
    |
760 | #                             "root_cause": rca.root_cause if rca else None,
761 | #                             "severity": rca.severity.value if rca else None,
762 | #                             "confidence": rca.confidence_score if rca else None,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
763 | #                         },
764 | #                         "proposed_fix": {
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:764:1: ERA001 Found commented-out code
    |
762 | #                             "confidence": rca.confidence_score if rca else None,
763 | #                         },
764 | #                         "proposed_fix": {
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
765 | #                             "fix_type": fix.fix_type.value,
766 | #                             "description": fix.description,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:765:1: ERA001 Found commented-out code
    |
763 | #                         },
764 | #                         "proposed_fix": {
765 | #                             "fix_type": fix.fix_type.value,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
766 | #                             "description": fix.description,
767 | #                             "commands": fix.commands,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:766:1: ERA001 Found commented-out code
    |
764 | #                         "proposed_fix": {
765 | #                             "fix_type": fix.fix_type.value,
766 | #                             "description": fix.description,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
767 | #                             "commands": fix.commands,
768 | #                             "risks": fix.risks,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:767:1: ERA001 Found commented-out code
    |
765 | #                             "fix_type": fix.fix_type.value,
766 | #                             "description": fix.description,
767 | #                             "commands": fix.commands,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
768 | #                             "risks": fix.risks,
769 | #                         },
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:768:1: ERA001 Found commented-out code
    |
766 | #                             "description": fix.description,
767 | #                             "commands": fix.commands,
768 | #                             "risks": fix.risks,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
769 | #                         },
770 | #                         "shadow_verification": {
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:770:1: ERA001 Found commented-out code
    |
768 | #                             "risks": fix.risks,
769 | #                         },
770 | #                         "shadow_verification": {
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
771 | #                             "passed": passed,
772 | #                             "shadow_id": env.id,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:771:1: ERA001 Found commented-out code
    |
769 | #                         },
770 | #                         "shadow_verification": {
771 | #                             "passed": passed,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
772 | #                             "shadow_id": env.id,
773 | #                             "health_score": env.health_score,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:772:1: ERA001 Found commented-out code
    |
770 | #                         "shadow_verification": {
771 | #                             "passed": passed,
772 | #                             "shadow_id": env.id,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
773 | #                             "health_score": env.health_score,
774 | #                         },
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:773:1: ERA001 Found commented-out code
    |
771 | #                             "passed": passed,
772 | #                             "shadow_id": env.id,
773 | #                             "health_score": env.health_score,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
774 | #                         },
775 | #                         "recommendation": "Review fix proposal and rerun when ready",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:775:1: ERA001 Found commented-out code
    |
773 | #                             "health_score": env.health_score,
774 | #                         },
775 | #                         "recommendation": "Review fix proposal and rerun when ready",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
776 | #                     }
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:776:1: ERA001 Found commented-out code
    |
774 | #                         },
775 | #                         "recommendation": "Review fix proposal and rerun when ready",
776 | #                     }
    | ^^^^^^^^^^^^^^^^^^^^^^^ ERA001
777 |
778 | #                     assert report["decision"] == "aborted"
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:778:1: ERA001 Found commented-out code
    |
776 | #                     }
777 |
778 | #                     assert report["decision"] == "aborted"
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
779 | #                     assert report["shadow_verification"]["passed"] is True
780 | #                     assert report["proposed_fix"]["fix_type"] is not None
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:779:1: ERA001 Found commented-out code
    |
778 | #                     assert report["decision"] == "aborted"
779 | #                     assert report["shadow_verification"]["passed"] is True
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
780 | #                     assert report["proposed_fix"]["fix_type"] is not None
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:780:1: ERA001 Found commented-out code
    |
778 | #                     assert report["decision"] == "aborted"
779 | #                     assert report["shadow_verification"]["passed"] is True
780 | #                     assert report["proposed_fix"]["fix_type"] is not None
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
781 |
782 | #             # Cleanup
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:783:1: ERA001 Found commented-out code
    |
782 | #             # Cleanup
783 | #             await mock_shadow_manager.cleanup(env.id)
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:802:1: ERA001 Found commented-out code
    |
800 | #         with patch("aegis.agent.graph._run_kubectl") as mock_kubectl:
801 | #             mock_kubectl.return_value = (
802 | #                 "Error: container killed by OOM handler\nFatal: out of memory"
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
803 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:803:1: ERA001 Found commented-out code
    |
801 | #             mock_kubectl.return_value = (
802 | #                 "Error: container killed by OOM handler\nFatal: out of memory"
803 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
804 |
805 | #             result = await analyze_incident(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:805:1: ERA001 Found commented-out code
    |
803 | #             )
804 |
805 | #             result = await analyze_incident(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
806 | #                 resource_type="pod",
807 | #                 resource_name="demo-api-xxx",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:806:1: ERA001 Found commented-out code
    |
805 | #             result = await analyze_incident(
806 | #                 resource_type="pod",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
807 | #                 resource_name="demo-api-xxx",
808 | #                 namespace="default",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:807:1: ERA001 Found commented-out code
    |
805 | #             result = await analyze_incident(
806 | #                 resource_type="pod",
807 | #                 resource_name="demo-api-xxx",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
808 | #                 namespace="default",
809 | #                 use_mock=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:808:1: ERA001 Found commented-out code
    |
806 | #                 resource_type="pod",
807 | #                 resource_name="demo-api-xxx",
808 | #                 namespace="default",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
809 | #                 use_mock=True,
810 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:809:1: ERA001 Found commented-out code
    |
807 | #                 resource_name="demo-api-xxx",
808 | #                 namespace="default",
809 | #                 use_mock=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
810 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:810:1: ERA001 Found commented-out code
    |
808 | #                 namespace="default",
809 | #                 use_mock=True,
810 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
811 |
812 | #             # RCA should have access to logs
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:813:1: ERA001 Found commented-out code
    |
812 | #             # RCA should have access to logs
813 | #             assert result.get("rca_result") is not None
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
814 |
815 | #     @pytest.mark.asyncio
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:823:1: ERA001 Found commented-out code
    |
821 | #         with patch("aegis.agent.graph._run_kubectl") as mock_kubectl:
822 | #             mock_kubectl.return_value = """
823 | #             Name: demo-api-xxx
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
824 | #             Status: CrashLoopBackOff
825 | #             Last State: Terminated
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:824:1: ERA001 Found commented-out code
    |
822 | #             mock_kubectl.return_value = """
823 | #             Name: demo-api-xxx
824 | #             Status: CrashLoopBackOff
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
825 | #             Last State: Terminated
826 | #             Reason: OOMKilled
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:826:1: ERA001 Found commented-out code
    |
824 | #             Status: CrashLoopBackOff
825 | #             Last State: Terminated
826 | #             Reason: OOMKilled
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
827 | #             """
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:829:1: ERA001 Found commented-out code
    |
827 | #             """
828 |
829 | #             result = await analyze_incident(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
830 | #                 resource_type="pod",
831 | #                 resource_name="demo-api-xxx",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:830:1: ERA001 Found commented-out code
    |
829 | #             result = await analyze_incident(
830 | #                 resource_type="pod",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
831 | #                 resource_name="demo-api-xxx",
832 | #                 namespace="default",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:831:1: ERA001 Found commented-out code
    |
829 | #             result = await analyze_incident(
830 | #                 resource_type="pod",
831 | #                 resource_name="demo-api-xxx",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
832 | #                 namespace="default",
833 | #                 use_mock=True,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:832:1: ERA001 Found commented-out code
    |
830 | #                 resource_type="pod",
831 | #                 resource_name="demo-api-xxx",
832 | #                 namespace="default",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
833 | #                 use_mock=True,
834 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:833:1: ERA001 Found commented-out code
    |
831 | #                 resource_name="demo-api-xxx",
832 | #                 namespace="default",
833 | #                 use_mock=True,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
834 | #             )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:834:1: ERA001 Found commented-out code
    |
832 | #                 namespace="default",
833 | #                 use_mock=True,
834 | #             )
    | ^^^^^^^^^^^^^^^ ERA001
835 |
836 | #             assert result.get("rca_result") is not None
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:836:1: ERA001 Found commented-out code
    |
834 | #             )
835 |
836 | #             assert result.get("rca_result") is not None
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:850:1: ERA001 Found commented-out code
    |
848 | #         """Verify K8sGPT is configured to use Ollama."""
849 | #         with patch.dict(os.environ, {"K8SGPT_BACKEND": "ollama"}):
850 | #             from aegis.agent.analyzer import K8sGPTAnalyzer
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
851 |
852 | #             analyzer = K8sGPTAnalyzer()
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:852:1: ERA001 Found commented-out code
    |
850 | #             from aegis.agent.analyzer import K8sGPTAnalyzer
851 |
852 | #             analyzer = K8sGPTAnalyzer()
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
853 | #             assert analyzer.backend == "ollama"
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:853:1: ERA001 Found commented-out code
    |
852 | #             analyzer = K8sGPTAnalyzer()
853 | #             assert analyzer.backend == "ollama"
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
854 |
855 | #     def test_k8sgpt_ollama_model_configuration(self) -> None:
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:873:1: ERA001 Found commented-out code
    |
871 | #     def test_abort_report_structure(self) -> None:
872 | #         """Test abort report has correct structure."""
873 | #         report = generate_abort_report(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
874 | #             resource_kind="Deployment",
875 | #             resource_name="demo-api",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:874:1: ERA001 Found commented-out code
    |
872 | #         """Test abort report has correct structure."""
873 | #         report = generate_abort_report(
874 | #             resource_kind="Deployment",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
875 | #             resource_name="demo-api",
876 | #             namespace="production",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:875:1: ERA001 Found commented-out code
    |
873 | #         report = generate_abort_report(
874 | #             resource_kind="Deployment",
875 | #             resource_name="demo-api",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
876 | #             namespace="production",
877 | #             rca_result=RCAResult(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:876:1: ERA001 Found commented-out code
    |
874 | #             resource_kind="Deployment",
875 | #             resource_name="demo-api",
876 | #             namespace="production",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
877 | #             rca_result=RCAResult(
878 | #                 root_cause="OOMKilled",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:877:1: ERA001 Found commented-out code
    |
875 | #             resource_name="demo-api",
876 | #             namespace="production",
877 | #             rca_result=RCAResult(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
878 | #                 root_cause="OOMKilled",
879 | #                 severity=IncidentSeverity.HIGH,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:878:1: ERA001 Found commented-out code
    |
876 | #             namespace="production",
877 | #             rca_result=RCAResult(
878 | #                 root_cause="OOMKilled",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
879 | #                 severity=IncidentSeverity.HIGH,
880 | #                 confidence_score=0.92,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:879:1: ERA001 Found commented-out code
    |
877 | #             rca_result=RCAResult(
878 | #                 root_cause="OOMKilled",
879 | #                 severity=IncidentSeverity.HIGH,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
880 | #                 confidence_score=0.92,
881 | #                 reasoning="Memory exceeded",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:880:1: ERA001 Found commented-out code
    |
878 | #                 root_cause="OOMKilled",
879 | #                 severity=IncidentSeverity.HIGH,
880 | #                 confidence_score=0.92,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
881 | #                 reasoning="Memory exceeded",
882 | #                 analysis_steps=["Step 1"],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:881:1: ERA001 Found commented-out code
    |
879 | #                 severity=IncidentSeverity.HIGH,
880 | #                 confidence_score=0.92,
881 | #                 reasoning="Memory exceeded",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
882 | #                 analysis_steps=["Step 1"],
883 | #                 evidence_summary=["Evidence 1"],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:882:1: ERA001 Found commented-out code
    |
880 | #                 confidence_score=0.92,
881 | #                 reasoning="Memory exceeded",
882 | #                 analysis_steps=["Step 1"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
883 | #                 evidence_summary=["Evidence 1"],
884 | #                 decision_rationale="Clear evidence",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:883:1: ERA001 Found commented-out code
    |
881 | #                 reasoning="Memory exceeded",
882 | #                 analysis_steps=["Step 1"],
883 | #                 evidence_summary=["Evidence 1"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
884 | #                 decision_rationale="Clear evidence",
885 | #                 affected_components=["pod/demo"],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:884:1: ERA001 Found commented-out code
    |
882 | #                 analysis_steps=["Step 1"],
883 | #                 evidence_summary=["Evidence 1"],
884 | #                 decision_rationale="Clear evidence",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
885 | #                 affected_components=["pod/demo"],
886 | #             ),
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:885:1: ERA001 Found commented-out code
    |
883 | #                 evidence_summary=["Evidence 1"],
884 | #                 decision_rationale="Clear evidence",
885 | #                 affected_components=["pod/demo"],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
886 | #             ),
887 | #             fix_proposal=FixProposal(
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:887:1: ERA001 Found commented-out code
    |
885 | #                 affected_components=["pod/demo"],
886 | #             ),
887 | #             fix_proposal=FixProposal(
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
888 | #                 fix_type=FixType.PATCH,
889 | #                 description="Increase memory",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:888:1: ERA001 Found commented-out code
    |
886 | #             ),
887 | #             fix_proposal=FixProposal(
888 | #                 fix_type=FixType.PATCH,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
889 | #                 description="Increase memory",
890 | #                 commands=["kubectl set resources..."],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:889:1: ERA001 Found commented-out code
    |
887 | #             fix_proposal=FixProposal(
888 | #                 fix_type=FixType.PATCH,
889 | #                 description="Increase memory",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
890 | #                 commands=["kubectl set resources..."],
891 | #                 confidence_score=0.85,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:890:1: ERA001 Found commented-out code
    |
888 | #                 fix_type=FixType.PATCH,
889 | #                 description="Increase memory",
890 | #                 commands=["kubectl set resources..."],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
891 | #                 confidence_score=0.85,
892 | #             ),
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:891:1: ERA001 Found commented-out code
    |
889 | #                 description="Increase memory",
890 | #                 commands=["kubectl set resources..."],
891 | #                 confidence_score=0.85,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
892 | #             ),
893 | #             shadow_result={"passed": True, "health_score": 0.95},
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:893:1: ERA001 Found commented-out code
    |
891 | #                 confidence_score=0.85,
892 | #             ),
893 | #             shadow_result={"passed": True, "health_score": 0.95},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
894 | #         )
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:894:1: ERA001 Found commented-out code
    |
892 | #             ),
893 | #             shadow_result={"passed": True, "health_score": 0.95},
894 | #         )
    | ^^^^^^^^^^^ ERA001
895 |
896 | #         assert "timestamp" in report
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:898:1: ERA001 Found commented-out code
    |
896 | #         assert "timestamp" in report
897 | #         assert "decision" in report
898 | #         assert report["decision"] == "aborted"
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
899 | #         assert "analysis" in report
900 | #         assert "proposed_fix" in report
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:927:1: ERA001 Found commented-out code
    |
925 | #     """
926 | #     return {
927 | #         "timestamp": datetime.now(UTC).isoformat(),
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
928 | #         "decision": "aborted",
929 | #         "reason": "User declined to apply fix to production cluster",
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:928:1: ERA001 Found commented-out code
    |
926 | #     return {
927 | #         "timestamp": datetime.now(UTC).isoformat(),
928 | #         "decision": "aborted",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
929 | #         "reason": "User declined to apply fix to production cluster",
930 | #         "resource": {
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:929:1: ERA001 Found commented-out code
    |
927 | #         "timestamp": datetime.now(UTC).isoformat(),
928 | #         "decision": "aborted",
929 | #         "reason": "User declined to apply fix to production cluster",
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
930 | #         "resource": {
931 | #             "kind": resource_kind,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:930:1: ERA001 Found commented-out code
    |
928 | #         "decision": "aborted",
929 | #         "reason": "User declined to apply fix to production cluster",
930 | #         "resource": {
    | ^^^^^^^^^^^^^^^^^^^^^^^ ERA001
931 | #             "kind": resource_kind,
932 | #             "name": resource_name,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:931:1: ERA001 Found commented-out code
    |
929 | #         "reason": "User declined to apply fix to production cluster",
930 | #         "resource": {
931 | #             "kind": resource_kind,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
932 | #             "name": resource_name,
933 | #             "namespace": namespace,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:932:1: ERA001 Found commented-out code
    |
930 | #         "resource": {
931 | #             "kind": resource_kind,
932 | #             "name": resource_name,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
933 | #             "namespace": namespace,
934 | #         },
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:933:1: ERA001 Found commented-out code
    |
931 | #             "kind": resource_kind,
932 | #             "name": resource_name,
933 | #             "namespace": namespace,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
934 | #         },
935 | #         "analysis": {
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:935:1: ERA001 Found commented-out code
    |
933 | #             "namespace": namespace,
934 | #         },
935 | #         "analysis": {
    | ^^^^^^^^^^^^^^^^^^^^^^^ ERA001
936 | #             "root_cause": rca_result.root_cause if rca_result else None,
937 | #             "severity": rca_result.severity.value if rca_result else None,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:936:1: ERA001 Found commented-out code
    |
934 | #         },
935 | #         "analysis": {
936 | #             "root_cause": rca_result.root_cause if rca_result else None,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
937 | #             "severity": rca_result.severity.value if rca_result else None,
938 | #             "confidence": rca_result.confidence_score if rca_result else None,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:937:1: ERA001 Found commented-out code
    |
935 | #         "analysis": {
936 | #             "root_cause": rca_result.root_cause if rca_result else None,
937 | #             "severity": rca_result.severity.value if rca_result else None,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
938 | #             "confidence": rca_result.confidence_score if rca_result else None,
939 | #             "reasoning": rca_result.reasoning if rca_result else None,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:938:1: ERA001 Found commented-out code
    |
936 | #             "root_cause": rca_result.root_cause if rca_result else None,
937 | #             "severity": rca_result.severity.value if rca_result else None,
938 | #             "confidence": rca_result.confidence_score if rca_result else None,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
939 | #             "reasoning": rca_result.reasoning if rca_result else None,
940 | #             "affected_components": rca_result.affected_components if rca_result else [],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:939:1: ERA001 Found commented-out code
    |
937 | #             "severity": rca_result.severity.value if rca_result else None,
938 | #             "confidence": rca_result.confidence_score if rca_result else None,
939 | #             "reasoning": rca_result.reasoning if rca_result else None,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
940 | #             "affected_components": rca_result.affected_components if rca_result else [],
941 | #         },
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:940:1: ERA001 Found commented-out code
    |
938 | #             "confidence": rca_result.confidence_score if rca_result else None,
939 | #             "reasoning": rca_result.reasoning if rca_result else None,
940 | #             "affected_components": rca_result.affected_components if rca_result else [],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
941 | #         },
942 | #         "proposed_fix": {
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:942:1: ERA001 Found commented-out code
    |
940 | #             "affected_components": rca_result.affected_components if rca_result else [],
941 | #         },
942 | #         "proposed_fix": {
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
943 | #             "fix_type": fix_proposal.fix_type.value if fix_proposal else None,
944 | #             "description": fix_proposal.description if fix_proposal else None,
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:943:1: ERA001 Found commented-out code
    |
941 | #         },
942 | #         "proposed_fix": {
943 | #             "fix_type": fix_proposal.fix_type.value if fix_proposal else None,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
944 | #             "description": fix_proposal.description if fix_proposal else None,
945 | #             "commands": fix_proposal.commands if fix_proposal else [],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:944:1: ERA001 Found commented-out code
    |
942 | #         "proposed_fix": {
943 | #             "fix_type": fix_proposal.fix_type.value if fix_proposal else None,
944 | #             "description": fix_proposal.description if fix_proposal else None,
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
945 | #             "commands": fix_proposal.commands if fix_proposal else [],
946 | #             "risks": fix_proposal.risks if fix_proposal else [],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:945:1: ERA001 Found commented-out code
    |
943 | #             "fix_type": fix_proposal.fix_type.value if fix_proposal else None,
944 | #             "description": fix_proposal.description if fix_proposal else None,
945 | #             "commands": fix_proposal.commands if fix_proposal else [],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
946 | #             "risks": fix_proposal.risks if fix_proposal else [],
947 | #             "rollback_commands": fix_proposal.rollback_commands if fix_proposal else [],
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:946:1: ERA001 Found commented-out code
    |
944 | #             "description": fix_proposal.description if fix_proposal else None,
945 | #             "commands": fix_proposal.commands if fix_proposal else [],
946 | #             "risks": fix_proposal.risks if fix_proposal else [],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
947 | #             "rollback_commands": fix_proposal.rollback_commands if fix_proposal else [],
948 | #         },
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:947:1: ERA001 Found commented-out code
    |
945 | #             "commands": fix_proposal.commands if fix_proposal else [],
946 | #             "risks": fix_proposal.risks if fix_proposal else [],
947 | #             "rollback_commands": fix_proposal.rollback_commands if fix_proposal else [],
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
948 | #         },
949 | #         "shadow_verification": shadow_result or {},
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:949:1: ERA001 Found commented-out code
    |
947 | #             "rollback_commands": fix_proposal.rollback_commands if fix_proposal else [],
948 | #         },
949 | #         "shadow_verification": shadow_result or {},
    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ERA001
950 | #         "recommendation": (
951 | #             "Review the proposed fix and rerun with --auto-fix when ready to apply. "
    |
    = help: Remove commented-out code

tests/integration/test_end_to_end_workflow.py:954:1: ERA001 Found commented-out code
    |
952 | #             "Or manually apply the fix using the commands provided."
953 | #         ),
954 | #     }
    | ^^^^^^^ ERA001
    |
    = help: Remove commented-out code

Found 441 errors.
No fixes available (6 hidden fixes can be enabled with the `--unsafe-fixes` option).

ruff-format..............................................................Failed
- hook id: ruff-format
- files were modified by this hook

18 files left unchanged

mypy.....................................................................Failed
- hook id: mypy
- exit code: 1
- files were modified by this hook

src/aegis/security/falco.py:103: error: Returning Any from function declared to return "dict[str, Any] | str"  [no-any-return]
src/aegis/security/pipeline.py:181: error: Unsupported target for indexed assignment ("dict[str, Any] | BaseException")  [index]
src/aegis/security/pipeline.py:182: error: Argument 1 to "append" of "list" has incompatible type "dict[str, Any] | BaseException"; expected "dict[str, Any]"  [arg-type]
src/aegis/security/pipeline.py:183: error: Item "BaseException" of "dict[str, Any] | BaseException" has no attribute "get"  [union-attr]
src/aegis/security/pipeline.py:188: error: Item "BaseException" of "dict[str, Any] | BaseException" has no attribute "get"  [union-attr]
src/aegis/security/pipeline.py:189: error: Item "BaseException" of "dict[str, Any] | BaseException" has no attribute "get"  [union-attr]
src/aegis/shadow/manager.py:1118: error: Returning Any from function declared to return "dict[str, Any] | None"  [no-any-return]
src/aegis/shadow/manager.py:1199: error: Returning Any from function declared to return "int | None"  [no-any-return]
src/aegis/shadow/manager.py:1202: error: Returning Any from function declared to return "int | None"  [no-any-return]
src/aegis/shadow/manager.py:1203: error: Returning Any from function declared to return "int | None"  [no-any-return]
src/aegis/cli.py:705: error: Unexpected keyword argument "fixType" for "FixProposal"; did you mean "fix_type"?  [call-arg]
src/aegis/cli.py:705: error: Unexpected keyword argument "confidenceScore" for "FixProposal"; did you mean "confidence_score"?  [call-arg]
src/aegis/cli.py:705: error: Unexpected keyword argument "estimatedDowntime" for "FixProposal"; did you mean "estimated_downtime"?  [call-arg]
Found 13 errors in 4 files (checked 46 source files)

Detect secrets...........................................................Failed
- hook id: detect-secrets
- files were modified by this hook
bandit...................................................................Failed
- hook id: bandit
- exit code: 1
- files were modified by this hook

[main]	INFO	profile include tests: None
[main]	INFO	profile exclude tests: B101
[main]	INFO	cli include tests: None
[main]	INFO	cli exclude tests: None
[main]	INFO	using config: pyproject.toml
[main]	INFO	running on Python 3.12.3
Working... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01
Run started:2026-02-03 12:00:31.678754

Test results:
>> Issue: [B404:blacklist] Consider possible security implications associated with the subprocess module.
   Severity: Low   Confidence: High
   CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
   More Info: https://bandit.readthedocs.io/en/0.0.0/blacklists/blacklist_imports.html#b404-import-subprocess
   Location: ./src/aegis/cli.py:21:0
20	import asyncio
21	import subprocess
22	import sys

--------------------------------------------------
>> Issue: [B603:subprocess_without_shell_equals_true] subprocess call - check for execution of untrusted input.
   Severity: Low   Confidence: High
   CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
   More Info: https://bandit.readthedocs.io/en/0.0.0/plugins/b603_subprocess_without_shell_equals_true.html
   Location: ./src/aegis/cli.py:1754:8
1753	    with log_path.open("wb") as handle:
1754	        subprocess.Popen(
1755	            cmd,
1756	            stdout=handle,
1757	            stderr=handle,
1758	            start_new_session=True,
1759	        )
1760	    return log_path

--------------------------------------------------
>> Issue: [B113:request_without_timeout] Call to requests without timeout
   Severity: Medium   Confidence: Low
   CWE: CWE-400 (https://cwe.mitre.org/data/definitions/400.html)
   More Info: https://bandit.readthedocs.io/en/0.0.0/plugins/b113_request_without_timeout.html
   Location: ./src/aegis/k8s_operator/handlers/shadow.py:212:37
211	        limits = resources.get("limits", {}) or {}
212	        cpu_total += _parse_quantity(requests.get("cpu") or limits.get("cpu"))
213	        mem_total += _parse_quantity(requests.get("memory") or limits.get("memory"))

--------------------------------------------------
>> Issue: [B113:request_without_timeout] Call to requests without timeout
   Severity: Medium   Confidence: Low
   CWE: CWE-400 (https://cwe.mitre.org/data/definitions/400.html)
   More Info: https://bandit.readthedocs.io/en/0.0.0/plugins/b113_request_without_timeout.html
   Location: ./src/aegis/k8s_operator/handlers/shadow.py:213:37
212	        cpu_total += _parse_quantity(requests.get("cpu") or limits.get("cpu"))
213	        mem_total += _parse_quantity(requests.get("memory") or limits.get("memory"))
214	    return cpu_total, mem_total

--------------------------------------------------
>> Issue: [B404:blacklist] Consider possible security implications associated with the subprocess module.
   Severity: Low   Confidence: High
   CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
   More Info: https://bandit.readthedocs.io/en/0.0.0/blacklists/blacklist_imports.html#b404-import-subprocess
   Location: src/aegis/cli.py:21:0
20	import asyncio
21	import subprocess
22	import sys

--------------------------------------------------
>> Issue: [B603:subprocess_without_shell_equals_true] subprocess call - check for execution of untrusted input.
   Severity: Low   Confidence: High
   CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
   More Info: https://bandit.readthedocs.io/en/0.0.0/plugins/b603_subprocess_without_shell_equals_true.html
   Location: src/aegis/cli.py:1754:8
1753	    with log_path.open("wb") as handle:
1754	        subprocess.Popen(
1755	            cmd,
1756	            stdout=handle,
1757	            stderr=handle,
1758	            start_new_session=True,
1759	        )
1760	    return log_path

--------------------------------------------------
>> Issue: [B113:request_without_timeout] Call to requests without timeout
   Severity: Medium   Confidence: Low
   CWE: CWE-400 (https://cwe.mitre.org/data/definitions/400.html)
   More Info: https://bandit.readthedocs.io/en/0.0.0/plugins/b113_request_without_timeout.html
   Location: src/aegis/k8s_operator/handlers/shadow.py:212:37
211	        limits = resources.get("limits", {}) or {}
212	        cpu_total += _parse_quantity(requests.get("cpu") or limits.get("cpu"))
213	        mem_total += _parse_quantity(requests.get("memory") or limits.get("memory"))

--------------------------------------------------
>> Issue: [B113:request_without_timeout] Call to requests without timeout
   Severity: Medium   Confidence: Low
   CWE: CWE-400 (https://cwe.mitre.org/data/definitions/400.html)
   More Info: https://bandit.readthedocs.io/en/0.0.0/plugins/b113_request_without_timeout.html
   Location: src/aegis/k8s_operator/handlers/shadow.py:213:37
212	        cpu_total += _parse_quantity(requests.get("cpu") or limits.get("cpu"))
213	        mem_total += _parse_quantity(requests.get("memory") or limits.get("memory"))
214	    return cpu_total, mem_total

--------------------------------------------------

Code scanned:
	Total lines of code: 20793
	Total lines skipped (#nosec): 0
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 4
		Medium: 4
		High: 0
	Total issues (by confidence):
		Undefined: 0
		Low: 4
		Medium: 0
		High: 4
Files skipped (0):

Lint Dockerfiles (hadolint)..............................................Failed
- hook id: hadolint
- exit code: 1
- files were modified by this hook

[0;34m[HADOLINT][0m Starting Dockerfile linting (1 file(s))
[1;33m[HADOLINT][0m Local hadolint not found, using Docker fallback
[0;34m[HADOLINT][0m Using Docker image: hadolint/hadolint:latest-alpine
[0;34m[HADOLINT][0m Linting: deploy/docker/Dockerfile
-:63 DL4006 [1m[93mwarning[0m: Set the SHELL option -o pipefail before RUN with a pipe in it. If you are using /bin/sh in an alpine image or if your shell is symlinked to busybox then consider explicitly setting your SHELL to /bin/ash, or disable this check
[0;31m[HADOLINT][0m Dockerfile linting failed

shellcheck...............................................................Failed
- hook id: shellcheck
- files were modified by this hook
Helm Lint................................................................Failed
- hook id: helm-lint
- files were modified by this hook

==> Linting deploy/helm/aegis-operator/
Error unable to check Chart.yaml file in chart: stat deploy/helm/aegis-operator/Chart.yaml: no such file or directory

Error: 1 chart(s) linted, 1 chart(s) failed
Helm not installed, skipping...

Terraform Format.....................................(no files to check)Skipped
Validate pyproject.toml..............................(no files to check)Skipped
```
