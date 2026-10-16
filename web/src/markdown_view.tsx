import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/** Safe, lazy CommonMark/GFM reading surface.
 * Model messages, imported documents and student writing are untrusted.
 * Raw HTML, MDX/JSX and remote images are intentionally not supported.
 */
export default function MarkdownView({ text, className = '' }: {
  text: string; className?: string;
}) {
  return <div className={'socratopia-markdown ' + className}>
    <Markdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      components={{
        a: ({ href, children }) => <a href={href} target="_blank"
          rel="noopener noreferrer nofollow">{children}</a>,
        img: () => null,
      }}>
      {text}
    </Markdown>
  </div>;
}
