/**
 * Hidden verification Q&A for lost item reporting (Section 6, V4.3).
 * Owner sets questions about physical details; answers encrypted and never shown again.
 */

const QUESTION_PLACEHOLDERS = [
  'e.g. What is written inside the cover?',
  'e.g. What was in the front pocket?',
  'e.g. What color is the inside lining?',
]

export default function OwnerVerificationQuestions({
  questions,
  onChange,
  onAdd,
  onRemove,
  answerWarnings = {},
}) {
  return (
    <div className="glass p-6">
      <h2 className="section-heading mb-1">
        Verification Questions <span className="text-red-500">*</span>
      </h2>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">
        Ask questions about details not visible in your description or photos.
        Your answers are encrypted and <strong>never shown to anyone</strong> after submission —
        a finder who has your item will answer them to prove they have it.
      </p>
      <div className="bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800
                      rounded-xl p-3 mb-3 text-xs text-brand-900 dark:text-brand-200">
        Ask questions about details not visible in your description or photos.
        Example: What is written inside? What is in the front pocket?
        What color is the lining? Avoid asking obvious things like color or brand.
      </div>
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700
                      rounded-xl p-3 mb-5 text-xs text-amber-800 dark:text-amber-300">
        <strong>Good questions:</strong> inside text · pocket contents · lining color · damage or stickers<br />
        <strong>Bad questions:</strong> color or brand already in your public description or photos
      </div>

      <div className="flex flex-col gap-5">
        {questions.map((q, idx) => (
          <div
            key={q.id}
            className="flex flex-col gap-3 p-4 rounded-xl
                       bg-slate-50 dark:bg-slate-800/50
                       border border-slate-200 dark:border-slate-700"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Question {idx + 1}
              </span>
              {questions.length > 2 && (
                <button
                  type="button"
                  onClick={() => onRemove(q.id)}
                  className="text-xs text-red-500 hover:text-red-700 transition-colors"
                >
                  Remove
                </button>
              )}
            </div>
            <input
              type="text"
              value={q.question}
              onChange={(e) => onChange(q.id, 'question', e.target.value)}
              placeholder={QUESTION_PLACEHOLDERS[idx] || 'Enter verification question'}
              maxLength={300}
              className="input-field"
              required
            />
            <input
              type="text"
              value={q.answer}
              onChange={(e) => onChange(q.id, 'answer', e.target.value)}
              placeholder="Your answer (encrypted — never shown again)"
              maxLength={300}
              className="input-field"
              required
            />
            {answerWarnings[q.id] && (
              <p className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30
                            rounded-lg px-3 py-2 border border-amber-200 dark:border-amber-700">
                {answerWarnings[q.id]}
              </p>
            )}
          </div>
        ))}
      </div>

      {questions.length < 3 && (
        <button
          type="button"
          onClick={onAdd}
          className="mt-4 text-sm text-brand-600 dark:text-brand-400
                     hover:text-brand-700 dark:hover:text-brand-300
                     font-medium transition-colors"
        >
          + Add another question
        </button>
      )}
    </div>
  )
}
