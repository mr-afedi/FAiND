/**
 * Shared Lucide icons — single source for category, trust, and UI glyphs.
 */
import {
  Smartphone,
  ShoppingBag,
  IdCard,
  Key,
  Shirt,
  BookOpen,
  Wallet,
  Gem,
  Package,
  Search,
  PartyPopper,
  MapPin,
  AlertTriangle,
  X,
  ChevronLeft,
  ChevronRight,
  Hand,
  ScanSearch,
  Flag,
  Trash2,
  Clock,
  Bot,
  Check,
  XCircle,
  Bell,
  Mail,
  Ban,
  Megaphone,
  Wrench,
  Star,
  ClipboardList,
  CircleDollarSign,
  Inbox,
  Lock,
  Globe,
  Zap,
  MessageCircle,
  Camera,
  Plus,
  Sparkles,
  PackageSearch,
} from 'lucide-react'

const defaultIconClass = 'w-4 h-4 shrink-0'

export const CATEGORY_META = {
  electronics: { Icon: Smartphone, label: 'Electronics' },
  bag:         { Icon: ShoppingBag, label: 'Bag / Backpack' },
  id_card:     { Icon: IdCard, label: 'ID / Card' },
  keys:        { Icon: Key, label: 'Keys' },
  clothing:    { Icon: Shirt, label: 'Clothing' },
  books_notes: { Icon: BookOpen, label: 'Books / Notes' },
  wallet:      { Icon: Wallet, label: 'Wallet' },
  jewellery:   { Icon: Gem, label: 'Jewellery' },
  other:       { Icon: Package, label: 'Other' },
}

export const CATEGORY_SELECT_OPTIONS = Object.entries(CATEGORY_META).map(([value, { label }]) => ({
  value,
  label,
}))

export function getCategoryMeta(category) {
  return CATEGORY_META[category] ?? CATEGORY_META.other
}

export function getCategoryLabel(category) {
  return getCategoryMeta(category).label
}

export function CategoryIcon({ category, className = defaultIconClass }) {
  const { Icon } = getCategoryMeta(category)
  return <Icon className={className} aria-hidden />
}

export function CategoryLabel({ category, className = 'inline-flex items-center gap-1.5' }) {
  const { Icon, label } = getCategoryMeta(category)
  return (
    <span className={className}>
      <Icon className={defaultIconClass} aria-hidden />
      <span>{label}</span>
    </span>
  )
}

export const TRUST_EVENT_META = {
  found_item_posted:       { label: 'Posted a found item', Icon: Package },
  successful_return:       { label: 'Successful item return', Icon: Check },
  failed_verification_2nd: { label: 'Failed verification (2nd try)', Icon: AlertTriangle },
  failed_verification_3rd: { label: 'Failed verification (3rd try)', Icon: AlertTriangle },
  false_claim_confirmed:   { label: 'Confirmed false claim', Icon: Ban },
  fraud_confirmed:         { label: 'Admin-confirmed fraud', Icon: Ban },
  user_report_received:    { label: 'User report received', Icon: Megaphone },
  admin_adjustment:        { label: 'Admin adjustment', Icon: Wrench },
}

export function TrustEventIcon({ reason, className = 'w-4 h-4 shrink-0' }) {
  const { Icon } = TRUST_EVENT_META[reason] ?? { Icon: Package, label: reason }
  return <Icon className={className} aria-hidden />
}

const NOTIFICATION_TYPE_META = {
  match_found:               Search,
  potential_match_expired:   Clock,
  verification_passed:       Check,
  verification_failed:       XCircle,
  verification_review:       Clock,
  claim_received:            Mail,
  item_returned:             PartyPopper,
  post_expiring:             Clock,
  account_suspended:         Ban,
  account_unsuspended:       Check,
  general:                   Megaphone,
  verified:                  Check,
  failed:                    XCircle,
  returned:                  PartyPopper,
  dispute:                   AlertTriangle,
  tip:                       CircleDollarSign,
  expiring:                  Clock,
  suspended:                 Ban,
}

export function NotificationTypeIcon({ type, className = 'w-5 h-5 shrink-0' }) {
  const Icon = NOTIFICATION_TYPE_META[type] ?? Bell
  return <Icon className={className} aria-hidden />
}

export function EmptyInboxIcon({ className = 'w-12 h-12 text-slate-400' }) {
  return <Inbox className={className} aria-hidden />
}

export {
  Smartphone,
  ShoppingBag,
  IdCard,
  Key,
  Shirt,
  BookOpen,
  Wallet,
  Gem,
  Package,
  Search,
  PartyPopper,
  MapPin,
  AlertTriangle,
  X,
  ChevronLeft,
  ChevronRight,
  Hand,
  ScanSearch,
  Flag,
  Trash2,
  Clock,
  Bot,
  Check,
  XCircle,
  Bell,
  Mail,
  Ban,
  Megaphone,
  Wrench,
  Star,
  ClipboardList,
  CircleDollarSign,
  Inbox,
  Lock,
  Globe,
  Zap,
  MessageCircle,
  Camera,
  Plus,
  Sparkles,
  PackageSearch,
}
