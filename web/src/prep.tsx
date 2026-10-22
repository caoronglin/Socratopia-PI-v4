function parseSections(body: string): Record<string, string> {
  const headings = [...body.matchAll(/^## ([^\n]+)\n/gm)];
  const values: Record<string, string> = {};
  headings.forEach((match, index) => {
    const name = match[1].trim();
    if (!['问题链', '预期证据', '教研会决议'].includes(name)) return;
    const start = (match.index ?? 0) + match[0].length;
    const end = index + 1 < headings.length ? headings[index + 1].index ?? body.length : body.length;
    values[name] = body.slice(start, end).replace(/\n+$/, '');
  });
  return values;
}

import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Collapse, Empty, Flex, Input, Listy, Modal, Row, Select, Space, Steps, Tag, Typography } from 'antd';
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
type PrepDocument = {
  lesson_id: string; chapter: string; status: string; editable: boolean;
  body: string; sha256: string; errors: string[]; warnings: string[];
  ready_granted: false; mastery_updated: false;
};

export default function PrepPanel({ course, request, onSelectLesson, onCreated, onOpenBook }: {
  course: string; request: CourseRequest;
  onSelectLesson: (lessonId: string) => void;
  onCreated: () => void;
  onOpenBook: () => void;
}) {
  const [modal, contextHolder] = Modal.useModal();
  const [book, setBook] = useState<Book | null>(null);
  const [lessons, setLessons] = useState<Record<string, string>>({});
  const [chapter, setChapter] = useState('');
  const [draft, setDraft] = useState<Draft | null>(null);
  const [selectedLesson, setSelectedLesson] = useState('');
  const [check, setCheck] = useState<Check | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [document, setDocument] = useState<PrepDocument | null>(null);
  const [editedBody, setEditedBody] = useState('');
  const [saved, setSaved] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const dirty = document !== null && editedBody !== document.body;
  const [structured, setStructured] = useState(false);
  const [fields, setFields] = useState<Record<string, string>>({});
  const sectionNames = ['问题链', '预期证据', '教研会决议'];
  const structuredDirty = document !== null && structured && sectionNames.some(name => fields[name] !== (parseSections(document.body)[name] ?? ''));

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
    onCreated();
  });

  const validate = (lesson: string) => void action(async () => {
    const result = await request<Check>('/courses/' + encodeURIComponent(course) +
      '/prep/' + encodeURIComponent(lesson));
    setSelectedLesson(lesson);
    setCheck(result);
  });

  const editorPath = (lesson: string) => '/courses/' + encodeURIComponent(course) +
    '/prep/' + encodeURIComponent(lesson) + '/document';

  const openEditor = (lesson: string) => void action(async () => {
    const latest = await request<PrepDocument>(editorPath(lesson));
    setDocument(latest); setEditedBody(latest.body); setFields(parseSections(latest.body)); setStructured(false);
    setSelectedLesson(lesson); setSaved(false); setShowPreview(false);
  });

  const confirmOpenEditor = (lesson: string) => {
    if (!dirty && !structuredDirty) { openEditor(lesson); return; }
    modal.confirm({
      title: '放弃尚未保存的修改？',
      content: '本地编辑内容尚未保存。打开另一份教案会丢弃这些修改。',
      okText: '放弃并打开', cancelText: '继续编辑',
      onOk: () => openEditor(lesson),
    });
  };

  const save = () => void action(async () => {
    if (!document?.editable || !dirty || !editedBody.trim()) return;
    const updated = await request<PrepDocument>(editorPath(document.lesson_id), 'PUT',
      { body: editedBody, expected_sha256: document.sha256 });
    setDocument(updated); setEditedBody(updated.body); setSaved(true);
    setCheck({ lesson_id: updated.lesson_id, status: updated.status,
      ready_for_class: false, errors: updated.errors, warnings: updated.warnings });
    setSelectedLesson(updated.lesson_id);
    await refresh();
    onCreated();
  });

  const saveStructured = () => void action(async () => {
    if (!document?.editable || !structuredDirty || dirty) return;
    const original = parseSections(document.body);
    const updates = Object.fromEntries(sectionNames.filter(name => name in original && fields[name] !== original[name]).map(name => [name, fields[name]]));
    const path = '/courses/' + encodeURIComponent(course) + '/prep/' + encodeURIComponent(document.lesson_id) + '/sections';
    const updated = await request<PrepDocument>(path, 'PUT', { updates, expected_sha256: document.sha256 });
    setDocument(updated); setEditedBody(updated.body); setFields(parseSections(updated.body)); setSaved(true);
    await refresh(); onCreated();
  });

  const discard = () => {
    if (!document) return;
    if (!dirty && !structuredDirty) { openEditor(document.lesson_id); return; }
    modal.confirm({
      title: '重新读取会丢弃当前修改',
      content: '如果其他窗口已经保存了内容，重新读取后可继续编辑最新版本。',
      okText: '丢弃并重新读取', cancelText: '继续编辑',
      onOk: () => openEditor(document.lesson_id),
    });
  };

  const chapterOptions = (book?.chapters || []).filter(c => c.level <= 2)
    .map(c => ({ label: c.title, value: c.title }));
  const step = !book?.available ? 0 : !draft ? 1 : draft.exists || draft.dry_run === false ? 3 : 2;

  return <div className="prep-workspace">
    {contextHolder}
    <Alert type="info" showIcon className="feedback" title="章节备课与正式课堂分离"
      description="按真实教材章节生成草稿，先预览再保存；保存草稿不会解锁 PREP ready、45 分钟计时或已验证掌握度。" />
    {error && <Alert className="feedback" type="error" showIcon title={error} />}
    <Card title="章节备课" extra={<Tag>PREP 状态机</Tag>}>
      <Steps size="small" current={step} responsive
        items={[{ title: '导入教材' }, { title: '选择章节' }, { title: '审核草稿' }, { title: '人工备课' }]} />
      <Paragraph type="secondary" className="section-note">
        使用现有教材目录；含小节的章自动生成对应教学单元，禁止人工填写不存在的章节标题。
      </Paragraph>
      {!book?.available ? <Empty description={<Space orientation="vertical">
        <Text>先导入主教材，再选择真实章节创建备课草稿。</Text>
        <Button type="primary" onClick={onOpenBook}>前往教材导入</Button>
      </Space>} /> : <>
        <Space wrap className="prep-actions">
          <Select aria-label="选择备课章节" showSearch={{ optionFilterProp: "label" }}
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
          {Object.keys(lessons).length ? <Listy
            items={Object.entries(lessons).map(([id, status]) => ({ id, status }))}
            rowKey="id"
            itemRender={({ id, status }) => <Flex align="center" justify="space-between" gap="middle" wrap="wrap">
              <Space><Text code>{id}</Text><Tag color={status === 'ready' ? 'green' :
                status === 'stale' || status === 'invalid' ? 'red' : 'default'}>{status}</Tag></Space>
              <Space size="small">
                <Button type="link" onClick={() => validate(id)}>检查</Button>
                <Button type="link" onClick={() => confirmOpenEditor(id)}>编辑草稿</Button>
              </Space>
            </Flex>} /> : <Empty description="还没有章节教案，先创建第一份草稿" />}
        </Col>
        <Col xs={24} md={12}>
          {check ? <>
            <Text strong>教案 {selectedLesson} · {check.status}</Text>
            <Paragraph type="secondary">检查只读；不会自动将 draft 改为 ready。</Paragraph>
            {!check.ready_for_class ? <Alert type="warning" showIcon title="尚未通过 ready 门禁"
              description={check.errors.length ? <ul>{check.errors.map((v, i) => <li key={i}>{v}</li>)}</ul> :
                "结构校验可以通过，但当前仍是 draft；须经人工审核并在权威 PREP 状态机标记 ready 后才可正式开课。"} /> :
              <Alert type="success" showIcon title="PREP 已通过结构及版本检查"
                description="开课仍由后端复核全课程 readiness、教材与计时条件。" />}
            {check.warnings.length > 0 && <Alert type="warning" showIcon className="feedback"
              title="待复核的提示" description={check.warnings.join('；')} />}
            <Button className="section-note" type="primary" onClick={() => onSelectLesson(selectedLesson)}>
              将 {selectedLesson} 带入课堂（不自动开课）
            </Button>
          </> : <Empty description="选择左侧教案进行状态检查" />}
        </Col>
      </Row>
    </Card>
    {document && <Card className="prep-editor" title={<Space wrap>
      <Text>教案正文 · {document.lesson_id}</Text>
      <Tag color={document.editable ? 'processing' : 'default'}>
        {document.editable ? '仅编辑 draft' : '只读'}
      </Tag>
      {(dirty || structuredDirty) && <Tag color="warning">有未保存更改</Tag>}
    </Space>} extra={<Button onClick={discard} disabled={loading}>重新读取</Button>}>
      <Paragraph type="secondary">
        教材版本、课号、章节范围与 PREP 状态由服务器保留。修改正文不会自动批准备课、解锁课堂或改变掌握度。
      </Paragraph>
      {!document.editable && <Alert type="warning" showIcon className="feedback"
        title="这份教案当前只读" description="只有 draft 可在网页编辑；已 ready 或旧版教案须按原有审核流程处理。" />}
      {saved && !dirty && <Alert type="success" showIcon className="feedback"
        title="教案已保存" description="保存结果已同步到本课程，下面的检查结果已按最新文件重新计算。" />}
      <Space wrap className="prep-editor-actions">
        <Button type={structured ? 'primary' : 'default'} disabled={dirty} onClick={() => setStructured(true)}>结构化编辑</Button>
        <Button type={!structured && !showPreview ? 'primary' : 'default'} disabled={structuredDirty} onClick={() => { setStructured(false); setShowPreview(false); }}>编辑 Markdown</Button>
        <Button type={showPreview ? 'primary' : 'default'} disabled={structuredDirty} onClick={() => { setStructured(false); setShowPreview(true); }}>文本预览</Button>
        {structured && <Button type="primary" loading={loading} onClick={saveStructured} disabled={!document.editable || !structuredDirty || dirty}>保存结构化字段</Button>}
        <Button type="primary" loading={loading} onClick={save}
          disabled={structured || !document.editable || !dirty || !editedBody.trim()}>保存草稿</Button>
      </Space>
      {structured ? <Space orientation="vertical" style={{ width: '100%' }}>{sectionNames.filter(name => name in parseSections(document.body)).map(name => <div key={name}><Text strong>{name}</Text><Input.TextArea aria-label={'编辑' + name} rows={5} value={fields[name] ?? ''} readOnly={!document.editable} onChange={event => { setFields(previous => ({ ...previous, [name]: event.target.value })); setSaved(false); }} /></div>)}</Space> : showPreview ? <pre className="prep-markdown prep-editor-preview">{editedBody}</pre> :
        <Input.TextArea aria-label="编辑 PREP 教案正文" rows={18} autoSize={false}
          placeholder="在此编辑教案正文" value={editedBody} maxLength={170000}
          readOnly={!document.editable} onChange={event => {
            setEditedBody(event.target.value); setSaved(false);
          }} className="prep-editor-input" />}
      <Flex align="center" justify="space-between" gap="small" wrap="wrap" className="prep-editor-footer">
        <Text type="secondary">保存前自动检查版本冲突。保留未写完的 TODO 是合法草稿，但不能开课。</Text>
        <Button onClick={() => validate(document.lesson_id)}>检查当前已保存版本</Button>
      </Flex>
      {document.errors.length > 0 && !dirty && <Alert type="info" showIcon className="feedback"
        title={`还有 ${document.errors.length} 项待完善`}
        description={<ul>{document.errors.slice(0, 10).map((item, index) =>
          <li key={index}>{item}</li>)}</ul>} />}
      {document.warnings.length > 0 && !dirty && <Alert type="warning" showIcon
        title="教案警告" description={document.warnings.join('；')} />}
    </Card>}
  </div>;
}
