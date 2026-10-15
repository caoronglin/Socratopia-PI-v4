import { useEffect, useState } from 'react';
import { Alert, Button, Card, Flex, Input, Select, Space, Switch, Tag, Typography } from 'antd';

type Request = <T,>(path: string, method?: string, body?: object) => Promise<T>;
type Agent = { agent_id: string; features: Record<string, boolean> };
type Life = { archived: boolean; archived_at: string | null };
type Route = { model: string; max_iterations: number; timeout_seconds: number };
type Models = { roles: Record<string, Route> };
const TASKS: Record<string, string> = { teach: '课程讲解', tutor: '导师讨论', explain_visual: '互动可视化',
  review: '审核与复习' };

export default function CourseSettings({ course, request }: { course: string; request: Request }) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [life, setLife] = useState<Life | null>(null);
  const [models, setModels] = useState<Models | null>(null);
  const [role, setRole] = useState('teach');
  const [model, setModel] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const path = '/courses/' + encodeURIComponent(course);
  const load = async () => {
    const [a,l,m] = await Promise.all([request<Agent>(path+'/agent'), request<Life>(path+'/lifecycle'),
      request<Models>(path+'/models')]); setAgent(a); setLife(l); setModels(m);
  };
  useEffect(() => { setAgent(null); setLife(null); setModels(null); setError(''); void load().catch(e =>
    setError(e instanceof Error ? e.message : '加载设置失败')); }, [course, request]);
  useEffect(() => { setModel(models?.roles[role]?.model || ''); }, [models, role]);
  const perform = async (action: () => Promise<void>) => {
    setBusy(true); setError('');
    try { await action(); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : '操作失败'); }
    finally { setBusy(false); }
  };
  return <Card title="课程 Agent · 能力与生命周期" extra={<Tag>{life?.archived ? '已归档' : '活动中'}</Tag>}>
    <Typography.Paragraph type="secondary">课程间独立模型路由与已核验记忆；Python 最终审核教材依据、学习时长及掌握记录。</Typography.Paragraph>
    {error && <Alert showIcon type="error" title={error} style={{ marginBottom: 12 }} />}
    {agent && <Space orientation="vertical" style={{ width: '100%' }}>
      <Typography.Text type="secondary">Agent ID：{agent.agent_id}</Typography.Text>
      <Flex align="center" gap={12} wrap="wrap">
        {(['memory','group','graph'] as const).map((key) => <Space key={key}>
          <Switch size="small" disabled={busy || life?.archived} checked={Boolean(agent.features[key])}
            onChange={enabled => void perform(async () => { await request(path+'/agent/features', 'POST', { feature: key, enabled }); })} />
          <Typography.Text>{({memory:'已核验问答记忆',group:'多导师协作',graph:'只读图谱工具'} as const)[key]}</Typography.Text>
        </Space>)}
      </Flex>
    </Space>}
    <Space direction="vertical" style={{ width: '100%', marginTop: 18 }}>
      <Typography.Text strong>任务级模型路由</Typography.Text>
      <Flex wrap="wrap" gap={8}>
        <Select aria-label="选择模型任务" style={{ width: 145 }} value={role} onChange={setRole}
          options={Object.entries(TASKS).map(([value,label]) => ({ value,label }))} />
        <Input aria-label="指定模型名称" style={{ minWidth: 180, flex: 1 }} value={model}
          onChange={e => setModel(e.target.value)} maxLength={120} placeholder="模型 ID" />
        <Button type="primary" loading={busy} disabled={!model.trim() || life?.archived}
          onClick={() => void perform(async () => { await request(path+'/models','POST',{role,model}); })}>保存</Button>
      </Flex>
      {models?.roles[role] && <Typography.Text type="secondary">
        上限：{models.roles[role].max_iterations} 次迭代 / {models.roles[role].timeout_seconds} 秒。模型不得写入课程权威状态。
      </Typography.Text>}
    </Space>
    <Flex align="center" gap={10} wrap="wrap" style={{ marginTop: 22 }}>
      <Button danger={!life?.archived} loading={busy} onClick={() => void perform(async () => {
        await request(path+'/lifecycle','POST',{archived:!life?.archived});
      })}>{life?.archived ? '恢复课程' : '归档课程'}</Button>
      <Typography.Text type="secondary">归档可恢复，保留教材、练习记录与历史；禁止新的课堂写入。</Typography.Text>
    </Flex>
  </Card>;
}
