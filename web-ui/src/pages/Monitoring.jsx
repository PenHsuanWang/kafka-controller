import React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Paper, Stack, Typography, TextField, Button, Chip, CircularProgress, Autocomplete, Divider, Box
} from "@mui/material";
import { getSnapshot, getRates } from "../api/monitoring";
import { listConsumerGroups } from "../api/groups";
import { listTopics } from "../api/topics";

/**
 * Simple minute heatstrip rendering onto canvas.
 * values = array of numbers (msgs/sec). We map min..p95 -> alpha.
 */
function HeatStrip({ values, height = 40 }) {
  const canvasRef = React.useRef(null);
  React.useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const ctx = c.getContext("2d");
    const w = c.width, h = c.height;
    ctx.clearRect(0, 0, w, h);
    if (!values.length) return;

    const vmax = quantile(values, 0.95) || 1;
    const col = (v) => {
      const a = Math.max(0.05, Math.min(1, v / vmax));
      // theme-agnostic: draw as black with varying alpha; MUI will place bg accordingly
      return `rgba(0,0,0,${a})`;
    };

    const step = Math.max(1, Math.floor(w / values.length));
    ctx.save();
    for (let i = 0; i < values.length; i++) {
      ctx.fillStyle = col(values[i] || 0);
      ctx.fillRect(w - (i + 1) * step, 0, step - 1, h);
    }
    ctx.restore();
  }, [values]);

  return (
    <canvas ref={canvasRef} width={window.innerWidth - 160} height={height} style={{ width: "100%", height }} />
  );
}

function quantile(arr, q) {
  if (!arr?.length) return 0;
  const a = [...arr].sort((x, y) => x - y);
  const p = (a.length - 1) * q;
  const b = Math.floor(p), t = p - b;
  if (a[b + 1] !== undefined) return a[b] + t * (a[b + 1] - a[b]);
  return a[b];
}

export default function Monitoring() {
  const qc = useQueryClient();

  // selections
  const [groupId, setGroupId] = React.useState("demo-group");
  const [groupInput, setGroupInput] = React.useState("demo-group");
  const [topic, setTopic] = React.useState("test-topic");
  const [topicInput, setTopicInput] = React.useState("test-topic");

  // options
  const groupsQuery = useQuery({
    queryKey: ["consumer-groups"],
    queryFn: () => listConsumerGroups(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  const topicsQuery = useQuery({
    queryKey: ["topics"],
    queryFn: listTopics,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  const groupOptions = React.useMemo(() => {
    const raw = groupsQuery.data ?? [];
    return raw
      .map((g) => {
        if (typeof g === "string") return g;
        if (g && typeof g === "object") return g.groupId ?? g.id ?? g.name ?? g[0];
        if (Array.isArray(g)) return g[0];
        return undefined;
      })
      .filter(Boolean);
  }, [groupsQuery.data]);

  const topicOptions = React.useMemo(
    () => (topicsQuery.data ?? []).map((t) => t?.name ?? t).filter(Boolean),
    [topicsQuery.data]
  );

  const enabled = !!groupId && !!topic;

  // ---- live rates buffer (60 seconds sliding window) ----
  const [samples, setSamples] = React.useState([]);
  const [auto, setAuto] = React.useState(true);

  // poll rates every 2s; push sample into sliding array (cap ~60s / 2s = 30 samples)
  React.useEffect(() => {
    if (!enabled || !auto) return;
    let cancelled = false;
    const loop = async () => {
      try {
        const r = await getRates(groupId, topic, 60);
        if (!cancelled) {
          const v = Number(r?.produceRate || 0);
          setSamples((prev) => {
            const next = [...prev, v].slice(-60); // keep last 60 samples
            return next;
          });
        }
      } catch {}
      if (!cancelled) setTimeout(loop, 2000);
    };
    loop();
    return () => { cancelled = true; };
  }, [enabled, auto, groupId, topic]);

  // snapshot (for lag / meta)
  const snapshotQuery = useQuery({
    queryKey: ["monitor-snapshot", groupId, topic],
    queryFn: () => getSnapshot(groupId, topic),
    enabled,
    refetchInterval: auto ? 5000 : false,
  });

  const latestRate = samples.length ? samples[samples.length - 1] : 0;
  const totalLag = snapshotQuery.data?.summary?.totalLag ?? 0;
  const maxLag = snapshotQuery.data?.summary?.maxLag ?? 0;
  const p95 = snapshotQuery.data?.summary?.timeLagP95Sec ?? null;

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Monitoring</Typography>

      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center">
          <Autocomplete
            freeSolo
            options={groupOptions}
            value={groupId}
            inputValue={groupInput}
            onChange={(_, v) => { setGroupId(v || ""); setGroupInput(v || ""); }}
            onInputChange={(_, v) => setGroupInput(v)}
            loading={groupsQuery.isFetching}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Group ID"
                size="small"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {groupsQuery.isFetching ? <CircularProgress size={16} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
            sx={{ minWidth: 280 }}
          />

          <Autocomplete
            freeSolo
            options={topicOptions}
            value={topic}
            inputValue={topicInput}
            onChange={(_, v) => { setTopic(v || ""); setTopicInput(v || ""); }}
            onInputChange={(_, v) => setTopicInput(v)}
            loading={topicsQuery.isFetching}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Topic"
                size="small"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {topicsQuery.isFetching ? <CircularProgress size={16} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
            sx={{ minWidth: 280 }}
          />

          <Button variant="contained" onClick={() => {
            qc.invalidateQueries({ queryKey: ["monitor-snapshot", groupId, topic] });
            setSamples([]); // reset buffer
          }} disabled={!enabled}>Load</Button>

          <Button variant={auto ? "contained" : "outlined"} onClick={() => setAuto(v => !v)} disabled={!enabled}>
            {auto ? "Auto On" : "Auto Off"}
          </Button>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack direction="row" spacing={1} sx={{ mb: 1 }} alignItems="center" flexWrap="wrap">
          <Typography variant="subtitle1">Throughput (msgs/sec)</Typography>
          <Chip size="small" label={`now: ${latestRate.toFixed(2)}`} />
          <Chip size="small" label={`p95: ${quantile(samples, 0.95).toFixed(2)}`} />
          <Chip size="small" color={totalLag > 0 ? (totalLag >= 1000 ? "error" : "warning") : "default"}
                label={`total lag: ${totalLag}`} />
          <Chip size="small" label={`max lag: ${maxLag}`} />
          <Chip size="small" label={`drift p95: ${p95 ?? "-"}`} />
        </Stack>

        <HeatStrip values={[...samples].reverse()} height={44} />
        <Box sx={{ display: "flex", justifyContent: "space-between", mt: 0.5 }}>
          <Typography variant="caption">-60s</Typography>
          <Typography variant="caption">now</Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle1" sx={{ mb: 1 }}>Latest snapshot</Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(0, 1fr))", gap: 1 }}>
          <Chip size="small" label={`Partitions: ${snapshotQuery.data?.summary?.partitions ?? "-"}`} />
          <Chip size="small" label={`Generated: ${snapshotQuery.data?.generatedAt ?? "-"}`} />
          <Chip size="small" label={`MaxLag Partition: ${snapshotQuery.data?.summary?.maxLagPartition ?? "-"}`} />
          <Chip size="small" label={`Topic: ${topic}`} />
          <Chip size="small" label={`Group: ${groupId}`} />
        </Box>
      </Paper>
    </Stack>
  );
}
