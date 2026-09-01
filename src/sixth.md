# 一个生产级质量的不安全双向链表双端队列

我们终于走到这一步了。我最大的宿敌：**[std::collections::LinkedList][linked-list]，双向链表双端队列**。

那个我曾试图摧毁却失败了的家伙。

我们的故事始于 2014 年即将结束之时，那时我们正飞快地逼近 Rust 1.0——Rust 的第一个稳定版本——的发布。我发现自己承担起了照料`std::collections`的角色，或者用我们当年亲切的叫法，libcollections。

多年来，libcollections 一直是所有人“可爱点子”和“大概有点用的东西”的倾倒场。在 Rust 还是一门羽翼未丰的实验性语言时，这一切都无伤大雅；可如果我的孩子们要离巢而去、走向稳定，它们就必须证明自己的价值。

在那之前，我鼓励并养育着它们所有人，但如今是时候让它们为自己的缺陷接受审判了。

我把爪子插进基岩，为我最愚蠢的那些孩子刻下墓碑。我把这座可怖的纪念碑立在城镇广场上，供所有人观瞻：

**[杀掉 TreeMap、TreeSet、TrieMap、TrieSet、LruCache 和 EnumSet](https://github.com/rust-lang/rust/pull/19955)**

它们的命运已被封定，因为我的话就是绝对。其余的集合被我的残暴吓坏了，但它们还没能逃过母亲的雷霆之怒。不久我又带着两块墓碑回来了：

**[废弃 BitSet 和 BitVec](https://github.com/rust-lang/rust/pull/26034)**

这对 Bit 双胞胎比它们倒下的同伴更狡猾，可惜没有足够的力量逃出我的手心。多数人以为我的活儿干完了，但我很快又取走了一个：

**[废弃 VecMap](https://github.com/rust-lang/rust/pull/26734)**

VecMap 试图靠隐匿求生 &mdash; 它是那么小，那么人畜无害！可这对我在未来图景中所看见的那个 libcollections 来说还不够。

我环视这片土地，看到还剩下些什么：

* Vec 和 VecDeque —— 结实而简单，计算之心脏。
* HashMap 和 HashSet —— 强大而睿智，计算之大脑。
* BTreeMap 和 BTreeSet —— 笨拙但不可或缺，计算之肝脏。
* BinaryHeap —— 灵巧而机敏，计算之脚踝。

我满意地点了点头。简单而有效。我的工作已经完&mdash;

不，[DList](https://github.com/rust-lang/rust/blob/0a84308ebaaafb8fd89b2fd7c235198e3ec21384/src/libcollections/dlist.rs)，这不可能！我以为你死在了那场悲惨的垃圾回收事故里！那场绝对是意外、完全不是蓄意的事故！

它们伪造了自己的死亡，换上了新名字，但它们还是原来那个：LinkedList，计算界那个鬼鬼祟祟、不可信任的阴谋家。

我向所有愿意听我说话的人宣扬它们的恶行，可人心不为所动。LinkedList 是个巧舌如簧的魔鬼，它说服了我身边的每一个人，让他们相信它是某种基础而自然的计算数据结构。它甚至说服了 C++ 相信它就是[*那个*list](https://en.cppreference.com/w/cpp/container/list)！

“一个标准库怎么能没有*LinkedList*呢？”

轻而易举！不费吹灰之力！

“它是非平凡的不安全代码，所以把它放进标准库是合理的！”

GPU 驱动和视频编解码器也是啊，libcollections 是极简主义的！

可惜啊，在我忙着对付它的亲族时，LinkedList 已经拉拢了太多盟友，也变得太过强大。

我逃回自己的实验室，试图炮制出某种能与之抗衡并将其摧毁的[邪恶克隆体](https://github.com/contain-rs/linked-list)或者[强化赛博格复制人](https://github.com/contain-rs/blist)，可我的科研经费被砍了，理由是我的研究“凶残邪恶得过分”之类的胡话。

LinkedList 赢了。我被击败，被迫流亡。

但现在你来了。你已经走到了这里。此刻你想必已经能理解 LinkedList 的堕落有多深了吧！来吧，我会把你需要知道的一切都教给你，好帮我把它彻底摧毁 &mdash; 也就是实现一个不安全的、生产级质量的双向链表双端队列所需要知道的一切。

有多“生产级”？嗯，我们要把我那个古老的 Rust 1.0 链表 crate 完全重写一遍，就是那个客观上比 std 里那个更好的库。那个在 2015 年就在稳定版 Rust 上提供了游标的库！而 2022 年的标准库至今还没有的东西！




[linked-list]: https://github.com/rust-lang/rust/blob/master/library/alloc/src/collections/linked_list.rs
