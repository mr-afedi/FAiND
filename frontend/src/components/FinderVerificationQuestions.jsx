/**
 * Hidden verification Q&A for found item reporting (Section 7, V4.2).
 * Finder sets questions + answers; answers are never shown again after submit.
 */

const QUESTION_PLACEHOLDERS = [
  'e.g. What color is the inside lining of the bag?',
  'e.g. Is there a scratch or damage anywhere? Describe it.',
  'e.g. What was inside the front pocket?',
]

export default function FinderVerificationQuestions({
  questions,
  onChange,
  onAdd,
  onRemove,
}) {
  return (
    <div className="glass p-6">
      <h2 className="section-heading mb-1">
        Verification Questions <span className="text-red-500">*</span>
      </h2>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">
        Set 2–3 questions only the real owner could answer about this physical item.
        Your answers are encrypted and <strong>never shown to anyone</strong> after submission —
        they are used to verify ownership when someone claims this item.
      </p>
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700
                      rounded-xl p-3 mb-5 text-xs text-amber-800 dark:text-amber-300">
        <strong>Good questions:</strong> inside lining color · specific damage or marks · what was in a pocket<br />
        <strong>Bad questions:</strong> &quot;What colour is it?&quot; or brand (visible in the photo)
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
              placeholder="Expected answer (encrypted — never shown again)"
              maxLength={300}
              className="input-field"
              required
            />
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
