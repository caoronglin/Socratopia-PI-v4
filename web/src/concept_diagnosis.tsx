import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Collapse, Empty, Flex, Input, Select, Space, Statistic, Tag, Typography } from 'antd';

type Request = <T,>(path: string, method?: string, body?: object) => Promise<T>;
type Node = { id: string; label: string; line: number };
type Edge = { source: string; target: string; type: string };
type Graph = { nodes: Node[]; edges: Edge[]; source_sha256: string; reviewed_prerequisites: number };
type Question = { id: string; stem: string; source_current: boolean };
type Concept = {
  concept_id: string; label: string; wrong_practice: number;
  attempted_practice: number; correct_practice: number;
  transfer_attempted: number; transfer_correct: number;
  next_action: string; transfer_questions: string[];
  prerequisite_checks: { concept_id: string; label: string; meaning: string; depth: number }[];
};
type Diagnosis = {
  concepts: Concept[]; priority_concepts: number; linked_questions: number;
  reviewed_prerequisites: number; transfer_verified: false; mastery_updated: false;
  note: string;
};
const { Text, Paragraph } = Typography;

export default function ConceptDiagnosis({ course, request, onPractice }: {
  course: string; request: Request; onPractice: () => void;
}) {
  const base = '/courses/' + encodeURIComponent(course);
  const [graph, setGraph] = useState<Graph | null>(null);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);
  const [prerequisite, setPrerequisite] = useState<string | undefined>();
  const [dependent, setDependent] = useState<string | undefined>();
  const [relationQuote, setRelationQuote] = useState('');
  const [questionId, setQuestionId] = useState<string | undefined>();
  const [conceptId, setConceptId] = useState<string | undefined>();
  const [role, setRole] = useState<'practice' | 'transfer'>('practice');
  const [questionQuote, setQuestionQuote] = useState('');

  const refresh = useCallback(async () => {
    const [g, d, q] = await Promise.all([
      request<Graph>(base + '/ontology'),
      request<Diagnosis>(base + '/diagnosis'),
      request<{ questions: Question[] }>(base + '/exercises'),
    ]);
    setGraph(g); setDiagnosis(d); setQuestions(q.questions);
  }, [base, request]);

  useEffect(() => {
    let valid = true;
    setGraph(null); setDiagnosis(null); setError('');
    void Promise.all([
      request<Graph>(base + '/ontology'),
      request<Diagnosis>(base + '/diagnosis'),
      request<{ questions: Question[] }>(base + '/exercises'),
    ]).then(([g, d, q]) => {
      if (valid) { setGraph(g); setDiagnosis(d); setQuestions(q.questions); }
    }).catch(err => {
      if (valid) setError(err instanceof Error ? err.message : '无法载入概念诊断');
    });
    return () => { valid = false; };
  }, [base, request]);

  const save = async (action: () => Promise<unknown>, message: string) => {
    if (busy) return;
    setBusy(true); setError(''); setSuccess('');
    try {
      await action();
      await refresh();
      setSuccess(message);
    } catch (err) {
      setError(err instanceof Error ? err.message : '关系保存失败');
    } finally { setBusy(false); }
  };

  const options = (graph?.nodes || []).map(n => ({ label: n.label, value: n.id }));
  const questionOptions = questions.filter(x => x.source_current).map(q => ({
    value: q.id, label: q.stem,
  }));

  return <div className="concept-diagnosis">
    <Card title="概念精准诊断" extra={<Tag>证据关联 · 人工审查</Tag>}>
      <Paragraph type="secondary">
        只根据已关联到教材概念的真实练习记录提出复习建议。
        前置关系需要人工审核；错题不能证明其前置知识一定薄弱。
      </Paragraph>
      {error && <Alert type="error" showIcon title={error} className="feedback" />}
      {success && <Alert type="success" showIcon title={success} className="feedback" />}
      {diagnosis && <Flex wrap="wrap" gap="large" className="concept-metrics">
        <Statistic title="待诊断概念" value={diagnosis.priority_concepts} />
        <Statistic title="关联练习" value={diagnosis.linked_questions} />
        <Statistic title="人工审查关系" value={diagnosis.reviewed_prerequisites} />
      </Flex>}
      {!diagnosis ? <Card loading variant="borderless" /> :
        diagnosis.concepts.length ? <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          {diagnosis.concepts.map(item => <Card type="inner" key={item.concept_id}
            title={<Flex wrap="wrap" gap="small" align="center">
              <Text>{item.label}</Text>
              {item.wrong_practice > 0 && <Tag color="warning">最近有 {item.wrong_practice} 道错题</Tag>}
              {item.transfer_correct > 0 && <Tag>迁移题有成功作答记录</Tag>}
            </Flex>}>
            <Text type="secondary">已作答的关联练习：{item.attempted_practice}；
              迁移题：{item.transfer_attempted}，其中答对 {item.transfer_correct}。</Text>
            {item.prerequisite_checks.length > 0 && <Paragraph className="section-note">
              <Text strong>建议核查前置知识：</Text>
              {item.prerequisite_checks.map(x => x.label).join('、')}。
              这些知识点尚未被证明薄弱。
            </Paragraph>}
            <Flex wrap="wrap" align="center" gap="small" style={{ marginTop: 12 }}>
              {item.next_action === 'review_and_check_prerequisites'
                ? <Tag color="processing">先复习相关概念，再核查前置知识</Tag>
                : item.next_action === 'attempt_transfer'
                  ? <Tag>建议进行迁移练习</Tag>
                  : <Tag>继续收集作答证据</Tag>}
              {item.transfer_questions.length > 0 && <Button size="small" onClick={onPractice}>
                前往课堂完成迁移练习
              </Button>}
            </Flex>
          </Card>)}
        </Space> : <Empty description="尚无已关联的概念练习。请在下方绑定题目与教材概念。" />}
      <Paragraph type="secondary" className="section-note">{diagnosis?.note}</Paragraph>
      <Button size="small" loading={busy} onClick={() => void save(async () => {}, '已重新读取当前教材数据')}>刷新诊断</Button>
    </Card>
    <Collapse items={[{
      key: 'relations', label: '审查前置知识关系',
      children: <Space orientation="vertical" style={{ width: '100%' }} size="middle">
        <Alert type="info" showIcon
          title="标题层级不等于知识依赖"
          description="只添加已核对的前置知识关系；教材原文引用必须逐字匹配，但引用匹配也不代表科学事实自动审核。" />
        <Select aria-label="选择前置概念" placeholder="先学什么？" showSearch={{ optionFilterProp: 'label' }}
          value={prerequisite} onChange={setPrerequisite} options={options} />
        <Select aria-label="选择依赖概念" placeholder="再学什么？" showSearch={{ optionFilterProp: 'label' }}
          value={dependent} onChange={setDependent} options={options} />
        <Input.TextArea rows={3} value={relationQuote} onChange={e => setRelationQuote(e.target.value)}
          maxLength={500} placeholder="从当前教材复制相关证据（8–500 字）" />
        <Button type="primary" loading={busy}
          disabled={!prerequisite || !dependent || prerequisite === dependent || relationQuote.trim().length < 8}
          onClick={() => void save(() => request(base + '/ontology/prerequisites', 'POST', {
            prerequisite_id: prerequisite, concept_id: dependent, source_quote: relationQuote,
          }), '已登记当前教材版本的前置关系')}>保存已审查前置关系</Button>
      </Space>,
    }, {
      key: 'questions', label: '关联练习与迁移题',
      children: <Space orientation="vertical" style={{ width: '100%' }} size="middle">
        <Alert type="info" showIcon
          title="迁移题须由使用者核实答案"
          description="系统不会直接生成可判定掌握的答案；需先在课堂创建有教材证据的客观题，再将其标记为练习或迁移题。" />
        <Select aria-label="选择待关联的练习题" placeholder="选择已审核的题目"
          showSearch={{ optionFilterProp: 'label' }} value={questionId}
          onChange={setQuestionId} options={questionOptions} />
        <Select aria-label="选择关联概念" placeholder="关联到哪个教材概念？"
          showSearch={{ optionFilterProp: 'label' }} value={conceptId}
          onChange={setConceptId} options={options} />
        <Select aria-label="练习目的" value={role} onChange={setRole}
          options={[{ value: 'practice', label: '基础理解/练习' }, { value: 'transfer', label: '迁移应用验证' }]} />
        <Input.TextArea rows={3} value={questionQuote} onChange={e => setQuestionQuote(e.target.value)}
          maxLength={500} placeholder="从当前教材复制相关证据（8–500 字）" />
        <Button type="primary" loading={busy}
          disabled={!questionId || !conceptId || questionQuote.trim().length < 8}
          onClick={() => void save(() => request(base + '/ontology/questions', 'POST', {
            question_id: questionId, concept_id: conceptId, role,
            source_quote: questionQuote,
          }), '已保存题目与概念的人工绑定')}>绑定题目与概念</Button>
      </Space>,
    }]} />
  </div>;
}
