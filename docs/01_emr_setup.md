# 01 · Creating the EMR cluster with HBase (AWS console, personal account)

This guide creates the **smallest cluster that runs HBase reliably**, using only the AWS web console and
a personal AWS account. The assignment is light (300 rows), so the cluster has no scaling, no task nodes,
and only the applications it needs.

Do the steps in order. Step 3 (the network check) is the one most often skipped. When it is skipped, the
cluster fails with *"The VPC/subnet configuration was invalid: No route to any external sources detected
in Route Table for Subnet…"*.

## Cluster specification

| Setting | Value | Why |
|---|---|---|
| Region | One region for everything, e.g. `us-east-1` (N. Virginia) or `us-east-2` (Ohio) | Key pairs, VPCs and clusters are regional; these two regions are the cheapest and offer every instance type |
| Release | `emr-7.14.0`, or the newest `emr-7.x` the console lists | Ships HBase 2.6.4 and the HBase Thrift server |
| Applications | HBase, Hadoop, ZooKeeper | HBase needs HDFS (Hadoop) and ZooKeeper; nothing else is used |
| HBase storage | HDFS | Simplest option. The data disappears with the cluster, which is fine because loading is scripted |
| Network | **Default VPC, public subnet** (route `0.0.0.0/0 → igw-…`) | EMR in a public subnet needs an internet gateway to reach the EMR service and S3 |
| Primary node | 1 × `m5.xlarge` (4 vCPU, 16 GiB), high availability **off** | Runs HMaster, ZooKeeper, the Thrift server and our Python scripts |
| Core node | 1 × `m5.xlarge` | Runs the RegionServer and the HDFS DataNode |
| Task nodes | none | Not needed |
| Scaling | manual, fixed size | AWS does not recommend managed scaling for HBase clusters |
| Auto-termination | after **3 hours** idle, **plus manual termination** when done | AWS does not support auto-termination with HBase, and SSH or HBase shell use does not count as activity. It is only a safety net (see 4.5) |
| Access | SSH (port 22) from **your IP only** | Port 9090 (Thrift) is never opened to the internet |

**Why not a single-node cluster?** EMR can run a cluster with only a primary node. On current releases,
though, AWS does not document whether the HBase RegionServer runs on the primary in that layout, so
1 primary + 1 core is the minimum that is known to work.

**Approximate cost (us-east-1, on demand):** each `m5.xlarge` costs about USD 0.192/h for EC2 plus
USD 0.048/h for EMR, roughly USD 0.48/h for both nodes. A 2–3 hour session costs about USD 1–1.50. A
cluster that fails to start ("Terminated with errors" before reaching *Waiting*) costs little or nothing.
Check current prices on the [EMR pricing page](https://aws.amazon.com/emr/pricing/).

---

## Step 1 · Choose the region

In the top-right corner of the console, select **US East (N. Virginia)** or **US East (Ohio)**. Both have
the same prices. You can choose another region if you prefer.
**Every following step must be done in that same region.** A key pair or VPC created in another region
does not appear in the EMR form.

Optional but recommended for a personal account: create a cost alert in **Billing and Cost Management →
Budgets → Create budget → Use a template → Monthly cost budget** (for example, USD 10) so you get an email
if something keeps running.

## Step 2 · Create the EC2 key pair

1. Open **EC2 → Network & Security → Key pairs → Create key pair**.
2. Fill in the form:
   - Name: `emr-hbase-key`
   - Key pair type: **RSA**
   - Private key file format: **.pem**
3. Click **Create key pair**. The browser downloads `emr-hbase-key.pem`. AWS does not keep a copy, so
   don't lose it.
4. On your laptop, move the key and protect it:

   ```bash
   mkdir -p ~/.ssh && mv ~/Downloads/emr-hbase-key.pem ~/.ssh/
   chmod 400 ~/.ssh/emr-hbase-key.pem
   ```

## Step 3 · Check the network: default VPC and a public subnet

EMR needs a subnet that can reach the internet. In a public subnet, its route table must contain a route
`0.0.0.0/0 → igw-…` (an internet gateway). The **default VPC** that AWS creates in every region already
meets this requirement. Problems appear when the form selects another VPC, for example one created for
another project, a VPC with only private subnets, or a VPC created with the "VPC only" option, which has no
internet gateway.

1. Open **VPC → Your VPCs** and find the VPC whose **Default VPC** column says **Yes**. Write down its ID
   (`vpc-…`).
   - **If no VPC is marked as default** (it was deleted at some point), go to **Actions → Create default
     VPC → Create default VPC**. AWS rebuilds it with one public subnet per Availability Zone, an internet
     gateway and the correct routes.
2. Select that VPC and check the **Details** tab: **DNS resolution = Enabled** and **DNS hostnames =
   Enabled**. EMR needs both, and the default VPC has them enabled.
3. Open **VPC → Subnets**, filter by that VPC ID, and click one subnet (for example, the one in
   `us-east-1a`). Check two things:
   - **Route table** tab: there is a row with **Destination `0.0.0.0/0`** and **Target `igw-…`**. If the
     target is `nat-…` or the row is missing, that subnet is not public: pick another subnet.
   - **Details** tab: **Auto-assign public IPv4 address = Yes**.
4. Write down that **subnet ID** (`subnet-…`). You will select it in step 4.4.

> **About the error you may have seen.** The message *"No route to any external sources detected in Route
> Table for Subnet: subnet-XXXX for VPC: vpc-YYYY"* means the subnet chosen for the cluster has no route
> to the internet. To find out which VPC was used, look up `vpc-YYYY` in **VPC → Your VPCs**: it is
> usually not the default one. Choosing the default VPC and a subnet that passes the check above fixes the
> error. You do not need to delete the failed cluster, and it costs nothing.

## Step 4 · Create the cluster

Open **Amazon EMR → EMR on EC2 → Clusters → Create cluster** and fill in the form from top to bottom.
Leave every field not mentioned here at its default value. Console labels can vary slightly between
console updates.

### 4.1 Name and applications

- **Name:** `practica2-hbase`
- **Amazon EMR release:** `emr-7.14.0` (or the newest `emr-7.x`)
- **Application bundle:** **Custom**, then tick only **HBase**, **Hadoop** and **ZooKeeper**. Untick
  everything else (Spark, Hive, Hue, Livy, Pig…). The "HBase" bundle also works, but it adds Hive, Hue and
  Phoenix, which this assignment does not use.
- **AWS Glue Data Catalog settings:** leave unticked.
- **HBase storage settings:** **HDFS**.

### 4.2 Cluster configuration

- Choose **Instance groups**, not instance fleets.
- **Primary:** instance type `m5.xlarge`. Leave **Use high availability** unticked. High availability
  launches 3 primary nodes, which triples the cost.
- **Core:** instance type `m5.xlarge`.
- **Task 1 of 1:** click **Remove instance group**. Then check that the **Summary** panel on the right
  shows only *1 Primary, 1 Core*. HBase does not use a task node, and a forgotten one adds about
  USD 0.24/h.
- EBS volumes: keep the defaults.

### 4.3 Cluster scaling and provisioning

- **Choose an option:** **Set cluster size manually**
- **Core:** instance(s) size **1**. If a Task row is still listed, set it to 0.

### 4.4 Networking (this fixes the VPC/subnet error)

- **Virtual private cloud (VPC):** click **Browse** and choose the **default VPC** from step 3.
- **Subnet:** click **Browse** and choose the **public subnet** you wrote down in step 3.
- **EC2 security groups (firewall):** keep the EMR-managed defaults. EMR creates
  `ElasticMapReduce-master` and `ElasticMapReduce-slave` in that VPC. The SSH rule is added after
  creation, in step 6.

### 4.5 Cluster termination and node replacement

- **Termination option:** **Automatically terminate cluster after idle time (Recommended)**
- **Idle time:** `3` hours

> **Auto-termination is only a safety net with HBase.** AWS documents that auto-termination is not
> supported with non-YARN applications such as HBase. EMR treats the cluster as idle when it has no YARN
> applications, no pending steps, no notebook connections and HDFS use below 10%, and **SSH sessions or
> HBase shell commands do not count as activity**. This has two consequences:
>
> - With a short idle time, the cluster can terminate **while you are working**, and the `emp` table goes
>   with it. 3 hours leaves room for the whole runbook. To change it on a running cluster, go to
>   **Properties → Cluster termination and node replacement → Edit**.
> - Do not count on the cluster shutting itself down. **Always terminate it manually** when you finish
>   (see [Terminate the cluster](#terminate-the-cluster)).
- **Use termination protection:** leave unticked. When it is ticked, the cluster can't be terminated
  until you untick it.
- Unhealthy node replacement: keep the default.

### 4.6 Bootstrap actions, Cluster logs, Tags, Software settings

- **Bootstrap actions** and **Software settings:** leave empty.
- **Cluster logs:** keep **Publish cluster-specific logs to Amazon S3** ticked with the default location
  (`s3://aws-logs-<account>-<region>/elasticmapreduce/`). If the cluster fails, these logs explain why.
  They take a few KB.
- **Tags:** optional, for example `project = practica2-hbase`.

### 4.7 Security configuration and EC2 key pair

- **Security configuration:** none.
- **Amazon EC2 key pair for SSH to the cluster:** choose `emr-hbase-key` from step 2. If it is not in the
  list, the key pair was created in another region.

### 4.8 Identity and Access Management (IAM) roles

A personal account usually has no EMR roles yet. The console can create them:

- **Amazon EMR service role:** **Create a service role**.
  - If the console asks for a **VPC**, **Subnet** and **Security group** for this role, choose the **same
    default VPC and public subnet as in 4.4**, and keep the default security group option. The role is
    scoped to these resources. If it points to a different subnet than the cluster, the launch fails with
    permission errors.
  - The console creates a role named like `AmazonEMR-ServiceRole-2026…`.
- **EC2 instance profile for Amazon EMR:** **Create an instance profile**.
  - **S3 bucket access:** **All S3 buckets in this account with read and write access**. This is the
    simplest choice for a personal practice account with nothing sensitive in S3. Otherwise, choose
    **Specific S3 buckets** and select the logs bucket.
  - The console creates a role named like `AmazonEMR-InstanceProfile-2026…`.

> **Retrying after a failed attempt.** If the first attempt created a service role scoped to the wrong
> subnet, do not reuse it. Choose **Create a service role** again, so the new role points to the correct
> subnet. Old unused roles cost nothing and can be deleted later in **IAM → Roles**.

### 4.9 Create

Review the **Summary** panel on the right:

- Release `emr-7.14.0`
- Applications: HBase, Hadoop, ZooKeeper
- Instances: 1 primary + 1 core `m5.xlarge`
- The VPC and subnet from step 3

Then click **Create cluster**.

## Step 5 · Wait until the cluster is ready

The cluster page shows the status. Click the refresh icon to update it.

| Status | Meaning |
|---|---|
| **Starting** | EC2 instances are being launched (3–5 min) |
| **Bootstrapping / Running** | Hadoop, ZooKeeper and HBase are being installed and started |
| **Waiting** | **Ready.** The cluster is idle and waiting for work. The idle timer starts counting here |
| **Terminated with errors** | Something failed. The reason appears next to the status and under **Properties → Status details**. See Troubleshooting |

Getting to **Waiting** usually takes 8–12 minutes.

## Step 6 · Allow SSH from your IP

1. On the cluster page, open the **Properties** tab, go to **Networking → EC2 security groups
   (firewall)**, and click the **Primary node** security group link (`ElasticMapReduce-master`). It opens
   in the EC2 console.
2. Open **Inbound rules → Edit inbound rules**.
3. If there is a rule **SSH / 22 / 0.0.0.0/0**, delete it, because it allows the whole internet.
4. Click **Add rule**:
   - **Type:** SSH (protocol TCP and port 22 are filled in automatically)
   - **Source:** **My IP**
5. Click **Save rules**.

If your home IP changes (new network or router restart), SSH stops working. Repeat this step to add your
new IP.

## Step 7 · Connect and check that HBase works

1. On the cluster **Summary**, copy the **Primary node public DNS**, for example
   `ec2-3-80-1-2.compute-1.amazonaws.com`.
2. Connect from your laptop:

   ```bash
   ssh -i ~/.ssh/emr-hbase-key.pem hadoop@<primary-public-dns>      # the user is always "hadoop"
   ```

   On the first connection, answer `yes` to the host fingerprint question.
3. On the primary node, check that HBase works. `2>/dev/null` hides the Java logging warnings (see the
   note below).

   ```bash
   hbase version 2>/dev/null | sed -n 1p
   echo "status" | hbase shell -n 2>/dev/null
   ss -ltn | grep 9090
   ```

   Expected output, as observed on `emr-7.14.0` in `us-east-2`:

   ```
   HBase 2.6.4-amzn-2
   1 active master, 0 backup masters, 1 servers, 0 dead, 2.0000 average load
   LISTEN 0      50      *:9090      *:*
   ```

   - `1 active master`: the HMaster is running on the primary node.
   - `1 servers`: there is one RegionServer, on the core node.
   - `*:9090`: the Thrift server accepts connections, which is what happybase uses.

   Without `2>/dev/null`, every `hbase` command first prints several `SLF4J: Class path contains
   multiple SLF4J bindings` lines. They are a harmless warning about duplicate logging libraries in EMR's
   classpath.

If all three commands answer as shown, the cluster is ready. Continue with step 3 of
[02_step_by_step.md](02_step_by_step.md#step-3--copy-the-repository-to-the-primary-node).

## How Python connects to HBase

```
 your laptop ──SSH (22)──▶ EMR primary node ─────────────────────────────▶ EMR core node
                           ├─ python3 src/analyze.py                         └─ RegionServer (data)
                           │     └─ happybase ──▶ localhost:9090
                           ├─ HBase Thrift server (9090) ──▶ HMaster / RegionServer
                           └─ hbase shell (fallback)
```

- **Recommended: run Python on the primary node.** The Thrift server is on `localhost:9090`, so no port
  needs to be opened. [`infra/setup_primary.sh`](../infra/setup_primary.sh) creates the virtual
  environment, installs `happybase`, makes sure Thrift is running and tests the connection.
- **Alternative: run Python on your laptop through an SSH tunnel.** This keeps port 9090 closed to the
  internet:

  ```bash
  ssh -i ~/.ssh/emr-hbase-key.pem -N -L 9090:localhost:9090 -L 16010:localhost:16010 hadoop@<primary-public-dns>
  # in another terminal, on the laptop:
  .venv/bin/python src/analyze.py --source thrift          # connects to localhost:9090 through the tunnel
  ```

  The same tunnel also exposes the HBase Master web UI at http://localhost:16010, which is useful for a
  screenshot of the table and its regions.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| *The VPC/subnet configuration was invalid: No route to any external sources detected in Route Table for Subnet…* | The subnet has no `0.0.0.0/0 → igw-…` route: it is private, or its VPC has no internet gateway. Do step 3 and choose the default VPC and a public subnet in 4.4 (and in 4.8 if the service role asks for them). If there is no default VPC, create it with **VPC → Actions → Create default VPC**. |
| The key pair does not appear in 4.7 | It was created in another region. Create it again in the cluster's region (step 2). |
| *Terminated with errors* mentioning permissions or `iam:PassRole` | The service role is scoped to a different subnet or VPC, or a role from a previous attempt was reused. Create a new service role in 4.8 with the same VPC and subnet as 4.4. |
| *Terminated with errors* mentioning capacity or an unsupported instance type | `m5.xlarge` is temporarily unavailable in that Availability Zone. Choose a public subnet in another AZ, or use `m5a.xlarge` / `m4.xlarge`. |
| *Terminated with errors* mentioning **block public access** | A security group allows inbound traffic from `0.0.0.0/0` on a port other than 22. Remove that rule and keep SSH limited to **My IP**. |
| `SLF4J: Class path contains multiple SLF4J bindings` before every `hbase` command | Harmless logging warning. Add `2>/dev/null` to hide it, as the runbook scripts do. |
| The cluster **Capacity** shows *1 Task* | The task group was not removed in 4.2. On a running cluster: **Instances (Hardware) → Instance groups → Task → Resize → 0**. |
| The cluster terminated by itself while you were working | Auto-termination counted it as idle (see 4.5). Create a new cluster with a longer idle time and rerun runbook steps 3–6. Everything is scripted, so the table and the results are rebuilt identically. |
| `ssh: connect to host ... timed out` | The SSH rule is missing or your IP changed. Repeat step 6. |
| `Permission denied (publickey)` | Wrong key file, or a user other than `hadoop`. Run `chmod 400` on the `.pem` file. |
| Nothing listens on port 9090 | Run `sudo systemctl start hbase-thrift`, or `sudo -u hbase /usr/lib/hbase/bin/hbase-daemon.sh start thrift`. If it still fails, use the shell fallback in the runbook. |
| `TTransportException` from happybase | The client and server Thrift settings differ. Check `hbase.regionserver.thrift.framed` and `hbase.regionserver.thrift.compact` in `/etc/hbase/conf/hbase-site.xml`, and pass `--transport framed` and/or `--protocol compact` to the scripts. |
| `pip install` fails building `thriftpy2` | Run `sudo dnf install -y gcc python3-devel`, then rerun `infra/setup_primary.sh`. |

## Terminate the cluster

**Do this manually even though auto-termination is on.** With HBase it is only a safety net (see 4.5).
When `results/` is safely on your laptop:

1. Go to **Amazon EMR → Clusters**, select `practica2-hbase`, and choose **Terminate**.
2. Confirm the dialog.
3. Wait for the status **Terminated** (5–10 min). Billing stops then.

HDFS data, including the `emp` table, is deleted with the cluster. To run everything again later, create
a new cluster with this guide. Choose **Choose an existing service role / instance profile** in 4.8 and
select the roles created this time, as long as you use the same subnet.

Leftovers that cost nothing or almost nothing, and that you may delete when the course is over:

- the IAM roles `AmazonEMR-…`;
- the security groups `ElasticMapReduce-…`;
- the S3 bucket `aws-logs-…`, which holds a few KB of logs.
