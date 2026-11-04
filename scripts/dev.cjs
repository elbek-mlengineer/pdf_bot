const { spawnSync } = require("node:child_process");

const fs = require("node:fs");
const { randomBytes } = require("node:crypto");

function docker(args, quiet = false, input) {
  const result = spawnSync("docker", args, {
    stdio: input ? ["pipe", "inherit", "inherit"] : quiet ? "ignore" : "inherit",
    input,
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

const envPath = ".env";
const contents = fs.readFileSync(envPath, "utf8");
if (!process.env.POSTGRES_PASSWORD && !/^POSTGRES_PASSWORD=.+$/m.test(contents)) {
  const password = randomBytes(32).toString("hex");
  fs.appendFileSync(envPath, "\nPOSTGRES_PASSWORD=" + password + "\n");
}
const db = docker(["compose", "up", "-d", "--wait", "postgres"]);
if (db !== 0) process.exit(db);
const rotate = docker(
  ["compose", "exec", "-T", "postgres", "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-U", "pdfuser", "-d", "pdfbot"],
  false,
  "\\getenv new_password POSTGRES_PASSWORD\nALTER ROLE pdfuser PASSWORD :'new_password';\n"
);
if (rotate !== 0) process.exit(rotate);
process.exitCode = docker(["compose", "up", "--build"]);
