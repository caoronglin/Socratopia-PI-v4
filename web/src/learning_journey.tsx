import { Alert, Button, Card, Flex, Steps, Tag, Typography } from 'antd';

export type LearningTab = 'class' | 'flashcards' | 'group' | 'prep' | 'course' | 'evidence';
type Props = {
  bookAvailable: boolean;
  prepCount: number;
  formalReady: boolean;
  onNavigate: (tab: LearningTab) => void;
};

const { Paragraph } = Typography;

/** Navigation guidance only; never evidence of lesson completion or mastery. */
export default function LearningJourney({ bookAvailable, prepCount, formalReady, onNavigate }: Props) {
  // A saved PREP draft is not a finished lesson. A formally ready lesson
  // has not yet been taught, so the classroom step stays in progress.
  const current = !bookAvailable ? 0 : formalReady ? 2 : 1;
  const next = !bookAvailable ? '请先导入本课程的主教材。' :
    !prepCount ? '选择教材的实际章节，预览并创建 PREP 草稿。' :
    !formalReady ? '已有教案草稿；仍须完成审查并通过后端 PREP 与课程就绪门禁。' :
    '课堂已达到初步就绪状态；开课仍由服务端再次核验，练习可在课堂中进行。';
  return <Card title="学习路径" className="journey-card"
    extra={<Tag color={formalReady ? 'success' : 'processing'}>{formalReady ? '课堂初步就绪' : '按步骤准备'}</Tag>}>
    <Steps size="small" responsive current={current}
      items={[{ title: '教材' }, { title: '章节备课' }, { title: '正式课堂' }, { title: '练习与复盘' }, { title: '记忆闪卡' }]} />
    <Paragraph type="secondary" className="journey-guidance">这些步骤用于导航，不代表自动完成课堂或判定知识掌握。</Paragraph>
    <Alert type={formalReady ? 'success' : 'info'} showIcon title="下一步" description={next} />
    <Flex gap="small" wrap="wrap" className="journey-actions">
      <Button onClick={() => onNavigate('evidence')}>打开教材</Button>
      <Button onClick={() => onNavigate('prep')} disabled={!bookAvailable}>章节备课</Button>
      <Button type={formalReady ? 'primary' : 'default'} onClick={() => onNavigate('class')}>进入课堂</Button>
      <Button onClick={() => onNavigate('flashcards')} disabled={!bookAvailable}>记忆闪卡</Button>
      <Button onClick={() => onNavigate('group')} disabled={!bookAvailable}>导师讨论</Button>
    </Flex>
  </Card>;
}
