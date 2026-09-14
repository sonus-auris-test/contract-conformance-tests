import json
import pathlib
import re
import subprocess
import tomllib
import unittest

SOURCE_REPO = "sonus-auris/sonus-auris-infra"
SOURCE_SHA = "269a9b493bd6498e9a368e3e8a022d37d876f9ca"
ENVIRONMENTS = ("preview", "staging", "production")


def run(*args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


class CounterpartInfraLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = pathlib.Path(__file__).resolve().parents[1]
        cls.root = cls.repo_root / "fixtures" / "infra-snapshot"
        cls.lock = json.loads((cls.repo_root / "infra-source-lock.json").read_text())
        cls.manifest = tomllib.loads((cls.root / ".ores-infra.toml").read_text())

    def test_snapshot_is_exactly_source_locked(self) -> None:
        self.assertEqual(self.lock["source_repo"], SOURCE_REPO)
        self.assertEqual(self.lock["head_sha"], SOURCE_SHA)
        self.assertEqual(self.lock["execution_mode"], "independent-oracle")
        for relative, expected_blob in self.lock["files"].items():
            path = self.root / relative
            self.assertTrue(path.is_file(), path)
            actual_blob = run("git", "hash-object", str(path), cwd=self.repo_root).stdout.strip()
            self.assertEqual(actual_blob, expected_blob, relative)

    def test_modules_first_provider_roots(self) -> None:
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(self.manifest["layout"], "modules")
        self.assertEqual(self.manifest["modules_root"], "modules")
        self.assertEqual(self.manifest["environments_root"], "environments")
        providers = self.manifest["providers"]
        self.assertEqual(providers["supabase"]["canonical_path"], "modules/supabase")
        self.assertEqual(providers["supabase"]["native_working_directory"], "modules")
        self.assertEqual(providers["cloudflare"]["canonical_path"], "modules/cloudflare")
        self.assertEqual(providers["neon"]["project_root"], "modules/neon")
        self.assertEqual(providers["neon"]["config"], "modules/neon/neon.ts")
        self.assertEqual(self.manifest["policy"]["state_isolation"], "per-provider-per-environment")

    def test_environment_roots_format_init_validate(self) -> None:
        run("terraform", "fmt", "-check", "-recursive", "modules/cloudflare/terraform", cwd=self.root)
        for environment in ENVIRONMENTS:
            env_root = self.root / "environments" / environment
            text = (env_root / "main.tf").read_text()
            self.assertIn('backend "s3" {}', text)
            self.assertRegex(text, r'source\s*=\s*"\.\./\.\./modules/cloudflare/terraform/worker-shell"')
            self.assertRegex(text, rf'environment\s*=\s*"{re.escape(environment)}"')
            run("terraform", "fmt", "-check", "-recursive", ".", cwd=env_root)
            run("terraform", "init", "-backend=false", "-input=false", cwd=env_root)
            run("terraform", "validate", "-no-color", cwd=env_root)

    def test_durable_object_bindings_are_environment_complete(self) -> None:
        wrangler = json.loads((self.root / "modules/cloudflare/durable-coordinator/wrangler.jsonc").read_text())
        binding = wrangler["durable_objects"]["bindings"][0]
        class_name = binding["class_name"]
        self.assertEqual(binding["name"], "COORDINATOR")
        self.assertEqual(wrangler["exports"][class_name]["type"], "durable-object")
        self.assertEqual(wrangler["exports"][class_name]["storage"], "sqlite")
        for environment in ENVIRONMENTS:
            env_binding = wrangler["env"][environment]["durable_objects"]["bindings"][0]
            self.assertEqual(env_binding["name"], binding["name"])
            self.assertEqual(env_binding["class_name"], class_name)


if __name__ == "__main__":
    unittest.main()
