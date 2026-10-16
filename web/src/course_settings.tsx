import { useEffect, useState } from 'react';
import { Alert, Button, Card, Flex, Input, Popconfirm, Select, Space, Switch, Tag, Typography } from 'antd';

type Request = <T,>(path: string, method?: string, body?: object) => Promise<T>;
type Agent = { agent_id: string; features: Record<string, boolean> };
type Life = { archived: boolean; archived_at: string | null };
type Route = { model: string; max_iterations: number; timeout_seconds: number };
type Models = { roles: Record<string, Route> };
type StudyTask = { id: string; kind: string; status: string; payload?: { title?: string } };
type Tasks = { tasks: StudyTask[] };
type SyncInfo = { webdav_configured: boolean; s3_configured: boolean };
type UploadInfo = { backend: string; sha256: string; files: number; already_exists: boolean };
const TASKS: Record<string, string> = { teach: '课程讲解', tutor: '导师讨论', explain_visual: '互动可视化',
  review: '审核与复习' };

export default function CourseSettings({ course, request }: { course: string; request: Request }) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [life, setLife] = useState<Life | null>(null);
  const [models, setModels] = useState<Models | null>(null);
  const [role, setRole] = useState('teach');
  const [model, setModel] = useState('');
  const [busy, setBusy] = useState(false);
  const [tasks, setTasks] = useState<StudyTask[]>([]);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskKind, setTaskKind] = useState('study');
  const [sync, setSync] = useState<SyncInfo | null>(null);
  const [uploaded, setUploaded] = useState<UploadInfo | null>(null);
  const [error, setError] = useState('');
  const path = '/courses/' + encodeURIComponent(course);
  const load = async () => {
    const [a,l,m,t,remote] = await Promise.all([request<Agent>(path+'/agent'), request<Life>(path+'/lifecycle'),
      request<Models>(path+'/models'), request<Tasks>(path+'/tasks'), request<SyncInfo>(path+'/sync')]);
    setAgent(a); setLife(l); setModels(m); setTasks(t.tasks); setSync(remote);
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
    <Space orientation="vertical" style={{ width: '100%', marginTop: 18 }}>
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
    <Card size="small" title="课程任务" style={{ marginTop: 20 }}>
      <Flex gap={8} wrap="wrap">
        <Input value={taskTitle} onChange={e => setTaskTitle(e.target.value)}
          maxLength={160} placeholder="本节想完成的任务" style={{ minWidth: 180, flex: 1 }} />
        <Select value={taskKind} onChange={setTaskKind} style={{ width: 120 }}
          options={[{value:'study',label:'学习'}, {value:'review',label:'复习'},
            {value:'visualize',label:'可视化'}, {value:'research',label:'资料调查'}]} />
        <Button disabled={busy || Boolean(life?.archived) || taskTitle.trim().length < 2}
          onClick={() => void perform(async () => {
            await request(path+'/tasks','POST',{title:taskTitle.trim(),kind:taskKind,
              request_id:crypto.randomUUID().replaceAll('-', '')});
            setTaskTitle('');
          })}>添加任务</Button>
      </Flex>
      <Space orientation="vertical" style={{ marginTop: 12, width: '100%' }}>
        {tasks.slice(-6).map(t => <Typography.Text key={t.id}>
          <Tag>{t.status}</Tag>{t.payload?.title || t.kind}
        </Typography.Text>)}
      </Space>
      <Typography.Paragraph type="secondary">任务只是持久待办，不会自行启动 Agent 循环。</Typography.Paragraph>
    </Card>
    <Card size="small" title="远程快照（手动）" style={{ marginTop: 16 }}>
      <Typography.Paragraph type="secondary">可能包含私人的笔记与对话。只上传可信远端，恢复需人工审核。</Typography.Paragraph>
      <Flex wrap="wrap" gap={10}>
        {(['webdav','s3'] as const).map(backend => <Popconfirm key={backend}
          title="确认上传含个人学习资料的快照？" okText="确认上传" cancelText="取消"
          onConfirm={() => void perform(async () => {
            setUploaded(await request<UploadInfo>(path+'/sync/upload','POST',
              {backend,acknowledged_private_data:true}));
          })}>
          <Button loading={busy} disabled={busy || (backend === 'webdav' ? !sync?.webdav_configured : !sync?.s3_configured)}>
            上传 {backend === 'webdav' ? 'WebDAV' : 'S3'}
          </Button>
        </Popconfirm>)}
      </Flex>
      {uploaded && <Alert type="success" showIcon style={{ marginTop: 12 }}
        title={uploaded.already_exists ? '已有相同快照' : '远程快照已上传'}
        description={uploaded.backend + ' · ' + uploaded.files + ' 个文件 · SHA256 ' + uploaded.sha256.slice(0,16) + '…'}/>}
    </Card>
    <Flex align="center" gap={10} wrap="wrap" style={{ marginTop: 22 }}>
      <Button danger={!life?.archived} loading={busy} onClick={() => void perform(async () => {
        await request(path+'/lifecycle','POST',{archived:!life?.archived});
      })}>{life?.archived ? '恢复课程' : '归档课程'}</Button>
      <Typography.Text type="secondary">归档可恢复，保留教材、练习记录与历史；禁止新的课堂写入。</Typography.Text>
    </Flex>
  </Card>;
}
