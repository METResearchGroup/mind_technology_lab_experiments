import qwen from "@/public/data/qwen_run.json";

export type QwenSteerRow = (typeof qwen.steering)[number];

export { qwen };

export function qwenSteerRow(
  goalId: string,
  alpha: number,
): QwenSteerRow | undefined {
  return qwen.steering.find(
    (row) =>
      row.goal_id === goalId && Math.abs(Number(row.alpha) - alpha) < 1e-9,
  );
}
