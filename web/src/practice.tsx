import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Checkbox, Collapse, Empty, Flex, Form, Input, Radio, Select, Space, Statistic, Tag, Typography } from 'antd';
import { Button as MobileButton, Checkbox as MobileCheckbox, Radio as MobileRadio } from 'antd-mobile';
import PracticeChart from './practice_chart';

const { Paragraph, Text } = Typography;
export type CourseRequest = <T,>(path: string, method?: string, body?: object) => Promise<T>;

type Question = {
  id: string; stem: string; kind: 'single_select' | 'multi_select';
  options: string[]; lesson_id?: string | null;
  source_sha256: string; source_current: boolean;
};
type Attempt = {
  exercise_id: string; request_id: string; selected_indices: number[];
  correct_indices: number[]; is_correct: boolean; explanation: string;
  source_quote: string; source_sha256: string; replayed: boolean; mastery_updated: false;
};
export type PracticeSummary = {
  attempts: number; correct: number; accuracy: number | null;
  question_count: number; mastery_updated: false;
  trend: { day: string; correct: number; incorrect: number }[];
};
type Props = {
  course: string; request: CourseRequest;
  onAnswered?: () => void;
};
const emptySummary: PracticeSummary = {
  attempts: 0, correct: 0, accuracy: null, question_count: 0, mastery_updated: false, trend: [],
};

function AnswerCard({ item, request, course, onAnswered }: {
  item: Question; request: CourseRequest; course: string; onAnswered: () => void;
}) {
  const [selected, setSelected] = useState<number[]>([]);
  const [result, setResult] = useState<Attempt | null>(null);
  const [pendingId, setPendingId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const multi = item.kind === 'multi_select';
  const choose = (indices: number[]) => {
    if (result) return;
    setSelected(indices);
    // A new deliberate choice is a new possible submission; a network retry
    // with unchanged choices preserves the request identifier.
    setPendingId('');
  };
  const submit = async () => {
    if (!selected.length || !item.source_current || submitting || result) return;
    const requestId = pendingId || crypto.randomUUID().replaceAll('-', '');
    setPendingId(requestId);
    setSubmitting(true);
    setError('');
    try {
      const response = await request<Attempt>(
        '/courses/' + encodeURIComponent(course) + '/exercises/' + item.id + '/submit',
        'POST', { request_id: requestId, selected_indices: selected },
      );
      setResult(response);
      onAnswered();
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法提交答案');
    } finally {
      setSubmitting(false);
    }
  };
  return <Card type="inner" className="practice-question" title={
    <Flex align="center" gap="small" wrap="wrap">
      <Text>{item.stem}</Text>
      <Tag>{multi ? '多选' : '单选'}</Tag>
      {!item.source_current && <Tag color="warning">教材已修订 · 题目停用</Tag>}
    </Flex>
  }>
    <div className="desktop-practice-options">
      {multi
        ? <Checkbox.Group disabled={Boolean(result) || !item.source_current} value={selected}
            onChange={values => choose(values.map(Number))}>
            <Space direction="vertical">
              {item.options.map((option, index) =>
                <Checkbox key={index} value={index}>{option}</Checkbox>)}
            </Space>
          </Checkbox.Group>
        : <Radio.Group disabled={Boolean(result) || !item.source_current}
            value={selected[0]} onChange={event => choose([Number(event.target.value)])}>
            <Space direction="vertical">
              {item.options.map((option, index) =>
                <Radio key={index} value={index}>{option}</Radio>)}
            </Space>
          </Radio.Group>}
    </div>
    <div className="mobile-practice-options">
      {multi
        ? <MobileCheckbox.Group value={selected.map(String)}
            onChange={values => choose(values.map(Number))}>
            <div className="mobile-choices">
              {item.options.map((option, index) =>
                <MobileCheckbox disabled={Boolean(result) || !item.source_current}
                  key={index} value={String(index)}>{option}</MobileCheckbox>)}
            </div>
          </MobileCheckbox.Group>
        : <MobileRadio.Group value={selected[0] === undefined ? '' : String(selected[0])}
            onChange={value => choose([Number(value)])}>
            <div className="mobile-choices">
              {item.options.map((option, index) =>
                <MobileRadio disabled={Boolean(result) || !item.source_current}
                  key={index} value={String(index)}>{option}</MobileRadio>)}
            </div>
          </MobileRadio.Group>}
    </div>
    {error && <Alert type="error" className="feedback" showIcon message={error} />}
    {result ? <div className="answer-explanation">
      <Alert showIcon type={result.is_correct ? 'success' : 'warning'}
        message={result.is_correct ? '回答正确' : '这次回答还不正确'}
        description={'正确选项：' + result.correct_indices.map(i => item.options[i]).join('、')} />
      <Paragraph>{result.explanation}</Paragraph>
      <Paragraph type="secondary"><Text strong>教材原文：</Text>{result.source_quote}</Paragraph>
      <Text type="secondary">来源 SHA-256：{result.source_sha256.slice(0, 16)}… · 练习结果不自动认定知识掌握</Text>
    </div> : <div className="answer-actions">
      <Button type="primary" disabled={!selected.length || !item.source_current}
        loading={submitting} onClick={() => void submit()} className="desktop-submit">提交答案</Button>
      <MobileButton color="primary" loading={submitting}
        disabled={!selected.length || !item.source_current} onClick={() => void submit()}
        className="mobile-submit">提交答案</MobileButton>
    </div>}
  </Card>;
}

export default function PracticePanel({ course, request, onAnswered }: Props) {
  const [items, setItems] = useState<Question[]>([]);
  const [summary, setSummary] = useState<PracticeSummary>(emptySummary);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stem, setStem] = useState('');
  const [kind, setKind] = useState<'single_select' | 'multi_select'>('single_select');
  const [options, setOptions] = useState<string[]>(['', '', '', '']);
  const [keys, setKeys] = useState<number[]>([0]);
  const [explanation, setExplanation] = useState('');
  const [quote, setQuote] = useState('');
  const [lessonId, setLessonId] = useState('');

  const reload = useCallback(async () => {
    const prefix = '/courses/' + encodeURIComponent(course);
    const [list, stats] = await Promise.all([
      request<{questions: Question[]}>(prefix + '/exercises'),
      request<PracticeSummary>(prefix + '/exercise-summary'),
    ]);
    setItems(list.questions);
    setSummary(stats);
  }, [course, request]);

  useEffect(() => {
    let current = true;
    void (async () => {
      try {
        const prefix = '/courses/' + encodeURIComponent(course);
        const [list, stats] = await Promise.all([
          request<{questions: Question[]}>(prefix + '/exercises'),
          request<PracticeSummary>(prefix + '/exercise-summary'),
        ]);
        if (current) { setItems(list.questions); setSummary(stats); }
      } catch (err) {
        if (current) setError(err instanceof Error ? err.message : '题库读取失败');
      }
    })();
    return () => { current = false; };
  }, [course, request]);

  const createQuestion = async () => {
    setLoading(true); setError('');
    try {
      await request('/courses/' + encodeURIComponent(course) + '/exercises', 'POST', {
        kind, stem: stem.trim(), options: options.map(s => s.trim()),
        correct_indices: keys, explanation: explanation.trim(),
        source_quote: quote.trim(), lesson_id: lessonId.trim() || null,
      });
      setStem(''); setExplanation(''); setQuote('');
      setOptions(['', '', '', '']); setKeys([0]);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存题目失败');
    } finally { setLoading(false); }
  };
  const valid = stem.trim() && options.every(s => s.trim()) && explanation.trim()
    && quote.trim().length >= 8 && keys.length && (!lessonId || /^lesson_[0-9]{3,}$/.test(lessonId));
  return <div className="class-practice">
    <Card title="课堂互动练习" extra={<Tag color="blue">后端确定性判分</Tag>}>
      <Paragraph type="secondary">
        练习直接在课堂内完成，答后展示标准答案与教材原文。题目由课程使用者审核并录入，
        不能将 AI 自行生成的答案当作标准答案。
      </Paragraph>
      {error && <Alert type="error" message={error} showIcon className="feedback" />}
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {items.length ? items.map(item => <AnswerCard key={item.id} item={item}
          request={request} course={course} onAnswered={() => {
            void reload().then(() => onAnswered?.()).catch(err =>
              setError(err instanceof Error ? err.message : '统计刷新失败'));
          }} />) : <Empty description="本课程暂无题目，可在下方创建来源可核对的练习" />}
      </Space>
    </Card>
    <div className="practice-insights">
      <Card title="练习表现" size="small">
        <Flex gap="large" wrap="wrap">
          <Statistic title="累计作答" value={summary.attempts} suffix="次" />
          <Statistic title="答对次数" value={summary.correct} suffix="次" />
          <Statistic title="练习正确率" value={summary.accuracy ?? 0} suffix="%" />
        </Flex>
        <PracticeChart data={summary.trend} />
        <Text type="secondary">展示实际作答记录，不代表知识掌握度或学习能力排名。</Text>
      </Card>
    </div>
    <Collapse className="practice-editor" items={[{
      key: 'author',
      label: '录入已核对的课堂题目',
      children: <Form layout="vertical" onFinish={() => void createQuestion()}>
        <Alert type="info" showIcon className="feedback"
          message="题目需要人工确认正确答案及解释"
          description="引用必须逐字出现在当前课程 book.md 中；教材更新后旧题自动暂停作答。" />
        <Form.Item label="题型">
          <Select value={kind} onChange={value => { setKind(value); setKeys(value === 'single_select' ? [0] : [0, 1]); }}
            options={[{value:'single_select', label:'单选题'}, {value:'multi_select', label:'多选题'}]} />
        </Form.Item>
        <Form.Item label="题干">
          <Input.TextArea maxLength={500} showCount value={stem}
            onChange={event => setStem(event.target.value)} placeholder="明确、可客观判分的问题" />
        </Form.Item>
        {options.map((option, index) => <Form.Item key={index} label={'选项 ' + String.fromCharCode(65 + index)}>
          <Input maxLength={180} value={option} placeholder="填写一个候选答案"
            onChange={event => setOptions(old => old.map((text, i) => i === index ? event.target.value : text))} />
        </Form.Item>)}
        <Form.Item label="正确选项">
          {kind === 'single_select'
            ? <Radio.Group value={keys[0]} onChange={event => setKeys([Number(event.target.value)])}
                options={options.map((_, index) => ({ label: String.fromCharCode(65 + index), value: index }))} />
            : <Checkbox.Group value={keys} onChange={values => setKeys(values.map(Number))}
                options={options.map((_, index) => ({ label: String.fromCharCode(65 + index), value: index }))} />}
        </Form.Item>
        <Form.Item label="答案解析">
          <Input.TextArea value={explanation} maxLength={1000} showCount
            placeholder="说明正确答案及其他选项不成立的原因" onChange={event => setExplanation(event.target.value)} />
        </Form.Item>
        <Form.Item label="教材原文（8–500 字，必须逐字匹配）">
          <Input.TextArea value={quote} maxLength={500} showCount
            placeholder="从当前课程的 book.md 复制对应的原始证据" onChange={event => setQuote(event.target.value)} />
        </Form.Item>
        <Form.Item label="所属课堂编号（可选）">
          <Input value={lessonId} placeholder="lesson_001"
            onChange={event => setLessonId(event.target.value)} />
        </Form.Item>
        <Button htmlType="submit" type="primary" loading={loading} disabled={!valid}>保存题目</Button>
      </Form>,
    }]} />
  </div>;
}
