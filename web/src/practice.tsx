import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Checkbox, Collapse, Empty, Flex, Form, Input, Radio, Select, Space, Statistic, Tag, Typography } from 'antd';
import { Button as MobileButton, Checkbox as MobileCheckbox, Radio as MobileRadio } from 'antd-mobile';
const PracticeChart = React.lazy(() => import('./practice_chart'));

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
type StudyItem = {
  exercise_id: string; stem: string; lesson_id: string | null;
  status: 'retry' | 'due' | 'new' | 'upcoming'; reason: string;
  next_review_at: string; recent_correct_streak: number;
};
type StudyPlan = {
  status: 'needs_textbook' | 'needs_questions' | 'ready';
  review_due: number; new_questions: number; stale_questions_excluded: number;
  suggested_minutes: number; items: StudyItem[]; upcoming: StudyItem[];
  mastery_updated: false; note: string;
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
  return <Card id={"practice-" + item.id} type="inner" className="practice-question" title={
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
            <Space orientation="vertical">
              {item.options.map((option, index) =>
                <Checkbox key={index} value={index}>{option}</Checkbox>)}
            </Space>
          </Checkbox.Group>
        : <Radio.Group disabled={Boolean(result) || !item.source_current}
            value={selected[0]} onChange={event => choose([Number(event.target.value)])}>
            <Space orientation="vertical">
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
    {error && <Alert type="error" className="feedback" showIcon title={error} />}
    {result ? <div className="answer-explanation">
      <Alert showIcon type={result.is_correct ? 'success' : 'warning'}
        title={result.is_correct ? '回答正确' : '这次回答还不正确'}
        description={'正确选项：' + result.correct_indices.map(i => item.options[i]).join('、')} />
      <Paragraph>{result.explanation}</Paragraph>
      <Paragraph type="secondary"><Text strong>教材原文：</Text>{result.source_quote}</Paragraph>
      <Text type="secondary">来源 SHA-256：{result.source_sha256.slice(0, 16)}… · 练习结果不自动认定知识掌握</Text>
      <div className="answer-actions"><Button size="small" onClick={() => { setResult(null); setSelected([]); setPendingId(''); }}>重新练习</Button></div>
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
  const [studyPlan, setStudyPlan] = useState<StudyPlan | null>(null);
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
    const [list, stats, plan] = await Promise.all([
      request<{questions: Question[]}>(prefix + '/exercises'),
      request<PracticeSummary>(prefix + '/exercise-summary'),
      request<StudyPlan>(prefix + '/study-plan'),
    ]);
    setItems(list.questions);
    setSummary(stats);
    setStudyPlan(plan);
  }, [course, request]);

  useEffect(() => {
    let current = true;
    void (async () => {
      try {
        const prefix = '/courses/' + encodeURIComponent(course);
        const [list, stats, plan] = await Promise.all([
          request<{questions: Question[]}>(prefix + '/exercises'),
          request<PracticeSummary>(prefix + '/exercise-summary'),
          request<StudyPlan>(prefix + '/study-plan'),
        ]);
        if (current) { setItems(list.questions); setSummary(stats); setStudyPlan(plan); }
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
    <Card title="今日高效学习" size="small" extra={<Tag>本地智能排序 · 无模型调用</Tag>}>
      {studyPlan?.status === 'needs_textbook'
        ? <Alert type="info" showIcon title="请先导入本课程的主教材，建立可核对的练习。" />
        : studyPlan?.status === 'needs_questions'
          ? <Alert type="info" showIcon title="还没有适用当前教材的练习题，可在下方录入。" />
          : studyPlan ? <>
            <Flex align="center" gap="large" wrap="wrap">
              <Statistic title="需要回顾" value={studyPlan.review_due} suffix="题" />
              <Statistic title="尚未尝试" value={studyPlan.new_questions} suffix="题" />
              <Statistic title="本次建议用时" value={studyPlan.suggested_minutes} suffix="分钟" />
            </Flex>
            <Paragraph type="secondary">
              先回顾上次错题，再做已到期的间隔练习，最后尝试新题。
              每次先自行回忆，再查看答案和教材证据。
            </Paragraph>
            {studyPlan.stale_questions_excluded > 0 &&
              <Alert type="warning" showIcon className="feedback"
                title={studyPlan.stale_questions_excluded + ' 道旧教材题目不参与本次计划'} />}
            <Space orientation="vertical" style={{ width: '100%' }}>
              {studyPlan.items.map((item, index) => <Flex key={item.exercise_id}
                align="center" justify="space-between" gap="small" wrap="wrap">
                <Space size="small" wrap>
                  <Tag color={item.status === 'retry' ? 'warning' : item.status === 'due' ? 'processing' : 'default'}>
                    {item.status === 'retry' ? '优先纠错' : item.status === 'due' ? '到期复习' : '新题'}
                  </Tag>
                  <Text>{index + 1}. {item.stem}</Text>
                  <Text type="secondary">{item.reason}</Text>
                </Space>
                <Button size="small" onClick={() =>
                  document.getElementById('practice-' + item.exercise_id)?.scrollIntoView({
                    behavior: 'smooth', block: 'center',
                  })}>前往作答</Button>
              </Flex>)}
              {!studyPlan.items.length &&
                <Text type="secondary">当前没有需要立即复习的题目，可以按自己的节奏休息或学习新章节。</Text>}
            </Space>
            <Paragraph type="secondary" className="section-note">{studyPlan.note}</Paragraph>
          </> : <Text type="secondary">正在读取本课程的学习建议…</Text>}
    </Card>
    <Card title="课堂互动练习" extra={<Tag color="blue">后端确定性判分</Tag>}>
      <Paragraph type="secondary">
        练习直接在课堂内完成，答后展示标准答案与教材原文。题目由课程使用者审核并录入，
        不能将 AI 自行生成的答案当作标准答案。
      </Paragraph>
      {error && <Alert type="error" title={error} showIcon className="feedback" />}
      <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
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
        <React.Suspense fallback={<div className="practice-chart" aria-label="加载练习趋势" />}><PracticeChart data={summary.trend} /></React.Suspense>
        <Text type="secondary">展示实际作答记录，不代表知识掌握度或学习能力排名。</Text>
      </Card>
    </div>
    <Collapse className="practice-editor" items={[{
      key: 'author',
      label: '录入已核对的课堂题目',
      children: <Form layout="vertical" onFinish={() => void createQuestion()}>
        <Alert type="info" showIcon className="feedback"
          title="题目需要人工确认正确答案及解释"
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
