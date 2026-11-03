const { spawnSync } = require("node:child_process");

function docker(args, quiet = false) {
  const result = spawnSync("docker", args, {
    stdio: quiet ? "ignore" : "inherit",
  });
  if (result.error) {
    console.error("Docker ishga tushmadi:", result.error.message);
    process.exit(1);
  }
  return result.status ?? 1;
}

if (docker(["info"], true) !== 0) {
  console.log("Docker Desktop ishga tushirilmoqda…");
  const status = docker(["desktop", "start", "--timeout", "180"]);
  if (status !== 0) process.exit(status);
}

process.exitCode = docker(["compose", "up", "--build"]);
