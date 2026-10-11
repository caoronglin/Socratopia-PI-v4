import { useCallback, useEffect, useState } from 'react';
import {
  Alert, Button, Card, Col, Divider, Empty, Flex, Input, Layout, List,
  Menu, Progress, Row, Select, Space, Statistic, Switch, Tag, Typography
} from 'antd';

type CourseState = {
  course: string;
  phase: string;
  lesson_id: string | null;
  current_chapter?: string;
  readiness: Record<string, string>;
  blockers: string[];
};
type Timer = {
  phase: string; elapsed_seconds?: number; remaining_seconds: number;
  minimum_seconds: number; completed: boolean; is_active?: boolean;
};
type Citation = { source_id: string; section: string; quote: string };
type Turn = { speaker: string; text: string; grounding?: string; citations?: Citation[]; fact_verified?: boolean; evidence?: { sha256: string; citations: Citation[]; grounding: string } };
type Evidence = { course: string; source: string; sha256: string; excerpts: { id: string; section: string; text: string }[]; ready: boolean };
type Overview = { course: string; book_available: boolean; grounded_chat_ready: boolean; formal_lesson_ready: boolean; blockers: string[]; timer_phase: string; group_phase: string };
type Group = {
  configured?: boolean; members?: string[]; next_speaker?: string | null;
  requires_user_turn?: boolean; grounding?: string; last_turn_evidence?: Citation[];
  session?: { topic: string; phase: string; round: number; max_rounds: number; turns: Turn[] } | null;
};
type WorkspaceProps = { dark: boolean; onDarkChange: (value: boolean) => void };
const { Sider, Header, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const tutorNames: Record<string, string> = { D: '三月七', E: '丹恒', F: '姬子', pi: 'Pi 导师', student: '我' };

export default function Workspace({ dark, onDarkChange }: WorkspaceProps) {
  const [token, setToken] = useState('');
  const [courses, setCourses] = useState<string[]>([]);
  const [course, setCourse] = useState('');
  const [tab, setTab] = useState('class');
  const [state, setState] = useState<CourseState | null>(null);
  const [timer, setTimer] = useState<Timer | null>(null);
  const [group, setGroup] = useState<Group | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [evidenceQuery, setEvidenceQuery] = useState('');
  const [lessonId, setLessonId] = useState('lesson_001');
  const [newCourse, setNewCourse] = useState('');
  const [newTutor, setNewTutor] = useState('F');
  const [message, setMessage] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [topic, setTopic] = useState('');
  const [members, setMembers] = useState<string[]>(['D', 'E']);
  const [lead, setLead] = useState('D');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const request = useCallback(async <T,>(path: string, method = 'GET', body?: object): Promise<T> => {
    if (!token) throw new Error('请先输入本地服务访问令牌');
    const response = await fetch('/api' + path, {
      method,
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    const result: unknown = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = result && typeof result === 'object' && 'detail' in result
        ? String(result.detail) : '请求失败，HTTP ' + response.status;
      throw new Error(detail);
    }
    return result as T;
  }, [token]);

  const run = async (action: () => Promise<void>) => {
    setBusy(true); setError('');
    try { await action(); }
    catch (err) { setError(err instanceof Error ? err.message : '未知错误'); }
    finally { setBusy(false); }
  };

  const reload = useCallback(async () => {
    if (!course || !token) return;
    const path = '/courses/' + encodeURIComponent(course);
    const [s, t, g, o] = await Promise.all([
      request<CourseState>(path + '/state'),
      request<Timer>(path + '/timer'),
      request<Group>(path + '/group'),
      request<Overview>(path + '/overview'),
    ]);
    setState(s); setTimer(t); setGroup(g); setOverview(o);
    if (s.lesson_id) setLessonId(s.lesson_id);
  }, [course, token, request]);

  useEffect(() => {
    setTurns([]);
    setEvidence(null);
    setOverview(null);
    setState(null);
    setGroup(null);
    setTimer(null);
  }, [course]);

  useEffect(() => {
    if (!course) return;
    void reload().catch((err: unknown) => setError(err instanceof Error ? err.message : '读取课程失败'));
  }, [course, reload]);

  const refreshCourses = async () => {
    await run(async () => {
      const result = await request<{courses: string[]}>('/courses');
      setCourses(result.courses);
      setCourse((previous) => result.courses.includes(previous) ? previous : (result.courses[0] || ''));
    });
  };
  const post = async <T,>(suffix: string, body: object = {}): Promise<T> =>
    request<T>('/courses/' + encodeURIComponent(course) + suffix, 'POST', body);

  const createCourse = async () => {
    if (!newCourse.trim()) return;
    await run(async () => {
      await request('/courses', 'POST', { name: newCourse.trim(), tutor: newTutor });
      const result = await request<{courses: string[]}>('/courses');
      setCourses(result.courses);
      setCourse(newCourse.trim());
      setNewCourse('');
    });
  };
  const searchEvidence = async () => {
    if (!evidenceQuery.trim() || !course) return;
    await run(async () => {
      const result = await request<Evidence>(
        '/courses/' + encodeURIComponent(course) + '/evidence?q=' + encodeURIComponent(evidenceQuery.trim())
      );
      setEvidence(result);
    });
  };
  const chat = async () => {
    const input = message.trim();
    if (!course || !input) return;
    await run(async () => {
      const reply = await post<Turn>('/chat', { message: input });
      setTurns((old) => [...old, { speaker: 'student', text: input }, reply]);
      setMessage('');
      await reload();
    });
  };
  const timerAction = async (action: string) => {
    await run(async () => {
      const next = action === 'start'
        ? await post<Timer>('/timer/start', { lesson_id: lessonId })
        : await post<Timer>('/timer/transition', { action });
      setTimer(next);
    });
  };
  const configureGroup = async () => {
    await run(async () => { setGroup(await post<Group>('/group/configure', { members, lead })); });
  };
  const startGroup = async () => {
    await run(async () => { setGroup(await post<Group>('/group/start', { topic, rounds: 2 })); });
  };
  const nextGroup = async () => {
    await run(async () => { setGroup(await post<Group>('/group/next')); });
  };
  const continueGroup = async () => {
    await run(async () => { setGroup(await post<Group>('/group/continue', {})); });
  };
  const activeSeconds = timer?.elapsed_seconds || 0;
  const minimum = timer?.minimum_seconds || 2700;
  const percent = Math.min(100, Math.round(activeSeconds / minimum * 100));

  return (
    <Layout className="shell">
      <Sider breakpoint="lg" collapsedWidth="0" width={232} theme={dark ? 'dark' : 'light'} className="sidebar">
        <div className="brand">Socratopia <span>v5</span></div>
        <Text type="secondary" className="brand-note">你的课程学习空间</Text>
        <Menu selectedKeys={[tab]} onClick={({ key }) => setTab(key)} mode="inline"
          items={[
            { key: 'class', label: '课堂与对话' },
            { key: 'group', label: '导师学习小组' },
            { key: 'course', label: '课程状态' },
            { key: 'evidence', label: '教材证据' },
          ]} />
      </Sider>
      <Layout>
        <Header className="topbar">
          <Space>
            <Text strong>学习工作台</Text>
            {course && <Tag color="blue">{course}</Tag>}
          </Space>
          <Space align="center"><Text type="secondary">深色模式</Text><Switch checked={dark} onChange={onDarkChange} /></Space>
        </Header>
        <Content className="content">
          <div className="page-heading">
            <Title level={3}>{tab === 'class' ? '课堂与对话' : tab === 'group' ? '学习小组' : tab === 'evidence' ? '教材证据' : '课程概览'}</Title>
            <Paragraph type="secondary">真实运行状态由 Python 服务管理，导师输出不会自动记为知识掌握。</Paragraph>
          </div>
          <Card size="small" className="control-card">
            <Flex gap="small" align="center" wrap="wrap">
              <Input.Password placeholder="服务令牌（仅保存在此页面内存）" value={token}
                onChange={e => setToken(e.target.value)} style={{ maxWidth: 280 }} />
              <Button onClick={() => void refreshCourses()} disabled={!token} loading={busy}>连接并刷新</Button>
              <Select placeholder="选择课程" value={course || undefined} onChange={setCourse}
                style={{ minWidth: 180 }} options={courses.map(name => ({ value: name, label: name }))} />
              <Button onClick={() => void run(reload)} disabled={!course} loading={busy}>刷新状态</Button>
            </Flex>
          </Card>
          {error && <Alert className="feedback" type="error" showIcon message={error} closable onClose={() => setError('')} />}
          {!course ? <Card title="开始新的课程">
            <Empty description="选择已初始化课程，或直接在这里新建课程骨架" />
            <Flex gap="small" justify="center" wrap="wrap" className="send-row">
              <Input placeholder="课程名称" value={newCourse}
                onChange={e => setNewCourse(e.target.value)} style={{ width: 240 }} />
              <Select value={newTutor} onChange={setNewTutor} style={{ minWidth: 120 }}
                options={['D','E','F'].map(value => ({value,label:tutorNames[value]}))} />
              <Button type="primary" disabled={!token || !newCourse.trim()} loading={busy}
                onClick={() => void createCourse()}>创建课程</Button>
            </Flex>
          </Card> : (
            <>
              {tab === 'class' && <>
                {!overview?.book_available && <Alert className="feedback" type="warning" showIcon
                  message="当前课程没有可用主教材"
                  description="请先在该课程 TEXTBOOK 目录准备 book.md；无教材时禁止 AI 凭记忆生成课程证据。" />}
                {overview?.book_available && <Alert className="feedback" type="info" showIcon
                  message="引用核验已启用"
                  description="模型必须提供来自本课程教材的逐字引文；引用通过不代表科学事实已被自动核实。" />}

                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={16}>
                    <Card title="教学对话" className="chat-card">
                      <List dataSource={turns} locale={{ emptyText: '输入一个问题，开始与 Pi 导师交互' }}
                        renderItem={(turn, index) => <List.Item key={index}>
                          <div className="chat-turn">
                            <Flex align="center" gap="small" wrap="wrap">
                              <Text strong>{tutorNames[turn.speaker] || turn.speaker}</Text>
                              {turn.grounding === 'citation_checked' && <Tag color="blue">已核对引文</Tag>}
                              {turn.grounding === 'insufficient_evidence' && <Tag>证据不足</Tag>}
                            </Flex>
                            <Paragraph className="message-text">{turn.text}</Paragraph>
                            {turn.citations?.map((citation, idx) =>
                              <Paragraph type="secondary" key={idx} className="quote">
                                <Text code>{citation.source_id}</Text> {citation.section}：{citation.quote}
                              </Paragraph>)}
                            </div>
                        </List.Item>} />
                      <Divider />
                      <Input.TextArea value={message} onChange={e => setMessage(e.target.value)}
                        placeholder="对课程提问，或解释你的解题思路…" rows={3} maxLength={2000} showCount />
                      <Flex justify="end" className="send-row">
                        <Button type="primary" loading={busy} disabled={!message.trim()} onClick={() => void chat()}>发送给 Pi</Button>
                      </Flex>
                    </Card>
                  </Col>
                  <Col xs={24} lg={8}>
                    <Card title="45 分钟课堂" extra={<Tag>{timer?.phase || '未开始'}</Tag>}>
                      <Statistic title="已核验有效时长" value={Math.floor(activeSeconds / 60)} suffix="分钟" />
                      <Progress percent={percent} />
                      <Text type="secondary">达到 2700 秒并满足课程门禁后，才能正式完成课堂。</Text>
                      <Divider />
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Input value={lessonId} onChange={e => setLessonId(e.target.value)} placeholder="lesson_001" />
                        <Space wrap>
                          <Button disabled={busy} onClick={() => void timerAction('start')}>开始</Button>
                          <Button disabled={busy || !timer?.is_active} onClick={() => void timerAction('pause')}>暂停</Button>
                          <Button disabled={busy || timer?.phase !== 'paused'} onClick={() => void timerAction('resume')}>继续</Button>
                          <Button type="primary" disabled={busy || activeSeconds < minimum} onClick={() => void timerAction('finish')}>完成课堂</Button>
                        </Space>
                        <Button danger disabled={busy || !timer || timer.phase === 'not_started'} onClick={() => void timerAction('interrupt')}>中断本课</Button>
                      </Space>
                    </Card>
                  </Col>
                </Row>
              </>}
              {tab === 'group' && <Row gutter={[16, 16]}>
                <Col xs={24} lg={9}>
                  <Card title="导师配置">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text>选择 2–3 位导师</Text>
                      <Select mode="multiple" value={members} onChange={setMembers}
                        options={Object.entries(tutorNames).filter(([id]) => ['D','E','F'].includes(id))
                          .map(([value, label]) => ({value, label}))} />
                      <Text>主持导师</Text>
                      <Select value={lead} onChange={setLead} options={members.map(m => ({value:m,label:tutorNames[m]}))} />
                      <Button disabled={busy || members.length < 2 || !members.includes(lead)}
                        onClick={() => void configureGroup()}>保存导师小组</Button>
                      <Divider />
                      <Input.TextArea rows={3} value={topic} maxLength={240} onChange={e => setTopic(e.target.value)}
                        placeholder="本轮要讨论的课程问题" />
                      <Button type="primary" disabled={busy || !group?.configured || !topic.trim()}
                        onClick={() => void startGroup()}>开始两轮讨论</Button>
                    </Space>
                  </Card>
                </Col>
                <Col xs={24} lg={15}>
                  <Card title="导师讨论" extra={<Tag>{group?.session?.phase || '未开始'}</Tag>}>
                    <List locale={{ emptyText: '配置导师与主题后开始讨论' }}
                      dataSource={group?.session?.turns || []}
                      renderItem={(turn, index) => <List.Item key={index}>
                        <div className="chat-turn"><Text strong>{tutorNames[turn.speaker]}</Text>
                          <Paragraph className="message-text">{turn.text}</Paragraph>
                          {turn.evidence?.citations.map((citation, j) =>
                            <Paragraph key={j} type="secondary" className="quote">
                              <Text code>{citation.source_id}</Text> {citation.section}：{citation.quote}
                            </Paragraph>)}
                          {turn.evidence && <Text type="secondary">来源摘要：{turn.evidence.sha256.slice(0, 16)}…</Text>}
                        </div>
                      </List.Item>} />
                    <Space wrap>
                      <Button type="primary" loading={busy} disabled={!group?.next_speaker}
                        onClick={() => void nextGroup()}>
                        请 {tutorNames[group?.next_speaker || ''] || '下一位导师'} 发言
                      </Button>
                      <Button disabled={busy || !group?.requires_user_turn} onClick={() => void continueGroup()}>
                        我已阅读，继续下一轮
                      </Button>
                    </Space>
                    {group?.last_turn_evidence?.map((source, index) =>
                      <Paragraph key={index} type="secondary" className="quote">
                        <Text code>{source.source_id}</Text> {source.section}：{source.quote}
                      </Paragraph>)}
                    <Paragraph type="secondary" className="section-note">导师独立生成回应并核对教材引文；讨论轮次由后端控制，回答不构成学生掌握证据。</Paragraph>
                  </Card>
                </Col>
              </Row>}
              {tab === 'evidence' && <Card title="检索主教材证据" extra={<Tag>只读</Tag>}>
                <Paragraph type="secondary">从当前课程 book.md 检索相关章节。所有引用显示原文及文件摘要，未验证来源的内容不会自动作为课堂事实。</Paragraph>
                <Flex gap="small" wrap="wrap">
                  <Input value={evidenceQuery} maxLength={2000} onChange={e => setEvidenceQuery(e.target.value)}
                    placeholder="输入要查证的概念或章节" style={{ maxWidth: 420 }} />
                  <Button disabled={!evidenceQuery.trim()} loading={busy}
                    onClick={() => void searchEvidence()}>检索证据</Button>
                </Flex>
                {evidence && <>
                  <Divider />
                  <Text type="secondary">来源：{evidence.source}</Text>
                  <Paragraph type="secondary" copyable={{text:evidence.sha256}}>SHA-256：{evidence.sha256.slice(0, 16)}…</Paragraph>
                  <List dataSource={evidence.excerpts}
                    locale={{emptyText:"当前问题未检索到匹配的教材段落"}}
                    renderItem={item => <List.Item>
                      <div className="chat-turn"><Text strong>{item.id} · {item.section}</Text>
                        <Paragraph className="message-text quote">{item.text}</Paragraph></div>
                    </List.Item>} />
                </>}
              </Card>}
              {tab === 'course' && <>
                <Card className="control-card" title="模块联动就绪情况">
                  <Flex gap="small" wrap="wrap">
                    <Tag color={overview?.book_available ? 'success' : 'warning'}>
                      教材：{overview?.book_available ? '可用' : '缺失'}
                    </Tag>
                    <Tag color={overview?.grounded_chat_ready ? 'success' : 'warning'}>
                      引文问答：{overview?.grounded_chat_ready ? '可尝试' : '阻断'}
                    </Tag>
                    <Tag color={overview?.formal_lesson_ready ? 'success' : 'warning'}>
                      正式课堂：{overview?.formal_lesson_ready ? '初步就绪' : '受阻'}
                    </Tag>
                    <Tag>计时：{overview?.timer_phase || '未知'}</Tag>
                    <Tag>学习小组：{overview?.group_phase || '未知'}</Tag>
                  </Flex>
                  <Paragraph className="section-note" type="secondary">
                    引文问答最终还需要问题相关段落；正式课堂须经 PREP 与课程计时器最终核验。
                  </Paragraph>
                </Card>
                <Card title="创建课程（仅补齐缺失骨架，不自动生成教材）" className="control-card">
                  <Flex wrap="wrap" gap="small">
                    <Input placeholder="新课程名称" value={newCourse}
                      onChange={e => setNewCourse(e.target.value)} style={{ maxWidth: 230 }} />
                    <Select value={newTutor} onChange={setNewTutor} style={{ minWidth: 130 }}
                      options={['D','E','F'].map(value => ({value,label:tutorNames[value]}))} />
                    <Button type="primary" loading={busy} disabled={!newCourse.trim()}
                      onClick={() => void createCourse()}>创建课程</Button>
                  </Flex>
                </Card>
                <Row gutter={[16, 16]}>
                <Col xs={24} lg={12}><Card title="课程进度">
                  <Statistic title="当前阶段" value={state?.phase || '尚未载入'} />
                  <Divider />
                  <Text>当前章节：{state?.current_chapter || '未定位'}</Text>
                  <br /><Text>课堂编号：{state?.lesson_id || '未指定'}</Text>
                  <Divider />
                  <Space wrap>{Object.entries(state?.readiness || {}).map(([name, value]) =>
                    <Tag key={name} color={value === 'ok' || value === 'clear' ? 'success' : 'warning'}>{name}: {value}</Tag>)}</Space>
                </Card></Col>
                <Col xs={24} lg={12}><Card title="检查与限制">
                  {state?.blockers?.length ? <Alert type="warning" showIcon
                    message="存在课堂阻断条件" description={state.blockers.join('、')} /> :
                    <Alert type="success" showIcon message="未记录课程阻断条件" />}
                  <Paragraph className="section-note" type="secondary">正式开课仍会由后端核对 PREP、教材版本和计时条件。</Paragraph>
                </Card></Col>
                </Row></>}
            </>
          )}
        </Content>
      </Layout>
    </Layout>
  );
}
