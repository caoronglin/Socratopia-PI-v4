import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Collapse, Empty, List, Row, Select, Space, Steps, Tag, Typography } from 'antd';
import type { CourseRequest } from './practice';

const { Paragraph, Text } = Typography;
type Chapter = { title: string; level: number; line: number };
type Book = { available: boolean; chapters: Chapter[] };
type LessonStatus = { course: string; lessons: Record<string, string> };
type Draft = {
  lesson_id: string; chapter: string; preview?: string; path: string;
  draft?: boolean; exists?: boolean; dry_run?: boolean; ready_granted?: boolean;
};
type Check = { lesson_id: string; status: string; ready_for_class: boolean; errors: string[]; warnings: string[] };

export default function PrepPanel({ course, request }: { course: string; request: CourseRequest }) {
  const [book, setBook] = useState<Book | null>(null);
  const [lessons, setLessons] = useState<Record<string, string>>({});
  const [chapter, setChapter] = useState('');
  const [draft, setDraft] = useState<Draft | null>(null);
  const [selectedLesson, setSelectedLesson] = useState('');
  const [check, setCheck] = useState<Check | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    const base = '/courses/' + encodeURIComponent(course);
    const [b, p] = await Promise.all([
      request<Book>(base + '/book'),
      request<LessonStatus>(base + '/prep')
    ]);
    setBook(b); setLessons(p.lessons);
  }, [course, request]);

  useEffect(() => {
    let current = true;
    void refresh().catch(err => { if (current) setError(err instanceof Error ? err.message : '备课状态读取失败'); });
    return () => { current = false; };
  }, [refresh]);

  const action = async (fn: () => Promise<void>) => {
    setLoading(true); setError('');
    try { await fn(); } catch (err) {
      setError(err instanceof Error ? err.message : '请求失败');
    } finally { setLoading(false); }
  };

  const preview = () => void action(async () => {
    if (!chapter) return;
    const result = await request<Draft>('/courses/' + encodeURIComponent(course) + '/prep/chapter/plan',
      'POST', { chapter, sources: [], apply: false });
    setDraft(result);
  });

  const create = () => void action(async () => {
    if (!draft || draft.exists || draft.chapter !== chapter) return;
    const result = await request<Draft>('/courses/' + encodeURIComponent(course) + '/prep/chapter/plan',
      'POST', { chapter, sources: [], apply: true });
    setDraft(result);
    setSelectedLesson(result.lesson_id);
    await refresh();
  });

  const validate = (lesson: string) => void action(async () => {
    const result = await request<Check>('/courses/' + encodeURIComponent(course) +
      '/prep/' + encodeURIComponent(lesson));
    setSelectedLesson(lesson);
    setCheck(result);
  });

  const chapterOptions = (book?.chapters || []).filter(c => c.level <= 2)
    .map(c => ({ label: c.title, value: c.title }));
  const step = !book?.available ? 0 : !draft ? 1 : draft.exists || draft.dry_run === false ? 3 : 2;

  return <div className="prep-workspace">
    <Alert type="info" showIcon className="feedback" message="章节备课与正式课堂分离"
      description="按真实教材章节生成草稿，先预览再保存；保存草稿不会解锁 PREP ready、45 分钟计时或已验证掌握度。" />
    {error && <Alert className="feedback" type="error" showIcon message={error} />}
    <Card title="章节备课" extra={<Tag>PREP 状态机</Tag>}>
      <Steps size="small" current={step} responsive
        items={[{ title: '导入教材' }, { title: '选择章节' }, { title: '审核草稿' }, { title: '人工备课' }]} />
      <Paragraph type="secondary" className="section-note">
        使用现有教材目录；含小节的章自动生成对应教学单元，禁止人工填写不存在的章节标题。
      </Paragraph>
      {!book?.available ? <Empty description="请先在「教材」页导入主教材" /> : <>
        <Space wrap className="prep-actions">
          <Select aria-label="选择备课章节" showSearch optionFilterProp="label"
            placeholder="选择教材章节" style={{ minWidth: 240, maxWidth: '100%' }}
            value={chapter || undefined} options={chapterOptions}
            onChange={value => { setChapter(value); setDraft(null); setCheck(null); }} />
          <Button disabled={!chapter} loading={loading} onClick={preview}>预览备课草稿</Button>
          <Button type="primary" disabled={!draft || draft.exists || !draft.dry_run || draft.chapter !== chapter}
            loading={loading} onClick={create}>保存草稿（不覆盖）</Button>
        </Space>
        {draft && <div className="prep-preview">
          <Space wrap><Tag color={draft.exists ? 'blue' : 'default'}>
            {draft.exists ? '已有教案，不重复创建' : draft.dry_run ? '仅预览，尚未保存' : '草稿已保存'}
          </Tag><Text code>{draft.lesson_id}</Text></Space>
          {draft.preview && <Collapse className="prep-collapse" items={[{
            key: 'preview', label: '查看完整 PREP 模板与待填写事项',
            children: <pre className="prep-markdown">{draft.preview}</pre>,
          }]} />}
        </div>}
      </>}
    </Card>
    <Card title="教案检查" className="control-card">
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <List size="small" dataSource={Object.entries(lessons)}
            locale={{ emptyText: '还没有章节教案，先创建第一份草稿' }}
            renderItem={([id, status]) => <List.Item>
              <Space><Text code>{id}</Text><Tag color={status === 'ready' ? 'green' :
                status === 'stale' || status === 'invalid' ? 'red' : 'default'}>{status}</Tag></Space>
              <Button type="link" onClick={() => validate(id)}>检查</Button>
            </List.Item>} />
        </Col>
        <Col xs={24} md={12}>
          {check ? <>
            <Text strong>教案 {selectedLesson} · {check.status}</Text>
            <Paragraph type="secondary">检查只读；不会自动将 draft 改为 ready。</Paragraph>
            {!check.ready_for_class ? <Alert type="warning" showIcon message="尚未通过 ready 门禁"
              description={check.errors.length ? <ul>{check.errors.map((v, i) => <li key={i}>{v}</li>)}</ul> :
                "结构校验可以通过，但当前仍是 draft；须经人工审核并在权威 PREP 状态机标记 ready 后才可正式开课。"} /> :
              <Alert type="success" showIcon message="PREP 已通过结构及版本检查"
                description="开课仍由后端复核全课程 readiness、教材与计时条件。" />}
            {check.warnings.length > 0 && <Alert type="warning" showIcon className="feedback"
              message="待复核的提示" description={check.warnings.join('；')} />}
          </> : <Empty description="选择左侧教案进行状态检查" />}
        </Col>
      </Row>
    </Card>
  </div>;
}
