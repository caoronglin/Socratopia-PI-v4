import { useEffect, useState } from 'react';
import { Alert, Button, Card, Empty, Flex, Tag, Typography } from 'antd';

type Node = { id: string; label: string; level: number; line: number; source: string };
type Edge = { source: string; target: string };
type Graph = { course: string; source_sha256: string; nodes: Node[];
  edges: Edge[]; truncated: boolean; fact_verified: false };
type Request = <T,>(path: string, method?: string, body?: object) => Promise<T>;

export default function CourseGraph({ course, request }: { course: string; request: Request }) {
  const [data, setData] = useState<Graph | null>(null);
  const [selected, setSelected] = useState<Node | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const load = async () => {
    setBusy(true); setError('');
    try { setData(await request<Graph>('/courses/' + encodeURIComponent(course) + '/graph')); }
    catch (e) { setError(e instanceof Error ? e.message : '图谱加载失败'); }
    finally { setBusy(false); }
  };
  useEffect(() => { setData(null); setSelected(null); void load(); }, [course, request]);
  const visible = data?.nodes.slice(0, 26) || [];
  const positions = new Map(visible.map((n, i) => [n.id, { x: 24 + (n.level - 1) * 176, y: 18 + i * 54 }]));
  const height = Math.max(150, visible.length * 54 + 28);
  return <Card title="教材知识图谱" extra={<Button size="small" loading={busy} onClick={() => void load()}>重新载入</Button>}>
    <Typography.Paragraph type="secondary">仅按教材原始章节标题建立层级关系；连线不是模型推断的科学因果。</Typography.Paragraph>
    {error && <Alert type="error" showIcon title={error} />}
    {data && <Flex gap={8} wrap="wrap"><Tag>节点 {data.nodes.length}</Tag>
      <Tag>关系 {data.edges.length}</Tag><Tag>教材 {data.source_sha256.slice(0, 12)}…</Tag>
      <Tag color="default">未经科学事实核验</Tag></Flex>}
    {!visible.length ? <Empty description="导入具有 Markdown 标题的教材后显示章节图谱" /> : <>
      <div className="course-graph-scroll">
        <svg viewBox={`0 0 760 ${height}`} role="img" aria-label="当前课程教材章节的从属关系图">
          {data?.edges.filter(e => positions.has(e.source) && positions.has(e.target)).map((edge, i) => {
            const a = positions.get(edge.source)!; const b = positions.get(edge.target)!;
            return <path key={i} d={`M ${a.x + 136} ${a.y + 17} C ${a.x + 156} ${a.y + 17}, ${b.x - 20} ${b.y + 17}, ${b.x} ${b.y + 17}`}
              fill="none" stroke="var(--ant-color-border)" strokeWidth={2}/>;
          })}
          {visible.map(n => { const pos = positions.get(n.id)!; return <g key={n.id}>
            <rect x={pos.x} y={pos.y} width={138} height={35} rx={8}
              fill={selected?.id === n.id ? 'var(--ant-color-primary-bg)' : 'var(--ant-color-bg-container)'}
              stroke="var(--ant-color-primary-border)"/>
            <text x={pos.x + 9} y={pos.y + 23} fontSize="12" fill="var(--ant-color-text)">
              {n.label.length > 10 ? n.label.slice(0, 10) + '…' : n.label}
            </text>
          </g>; })}
        </svg>
      </div>
      <Flex wrap="wrap" gap={8} style={{ marginTop: 14 }}>
        {visible.map(node => <Button key={node.id} size="small" type={selected?.id === node.id ? 'primary' : 'default'}
          onClick={() => setSelected(node)}>{node.label}</Button>)}
      </Flex>
      {selected && <Alert style={{ marginTop: 12 }} type="info" title={selected.label}
        description={`来自当前课程 book.md 第 ${selected.line} 行。此关系由标题层级确定，不证明概念因果。`} />}
      {(data?.truncated || (data?.nodes.length || 0) > visible.length) && <Typography.Paragraph type="secondary">仅展示前 26 个节点，完整图谱可通过 API 读取。</Typography.Paragraph>}
    </>}
  </Card>;
}
