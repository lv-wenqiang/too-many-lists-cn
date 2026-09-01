# 析构与 panic 安全性

话说，你注意到这条注释了吗：

```rust
// Note that we don't need to mess around with `take` anymore
// because everything is Copy and there are no dtors that will
// run if we mess up... right? :) Riiiight? :)))
```

它说得对吗？

不好意思，你忘了自己在读哪本书了吗？它当然是错的！（算是吧。）

我们再看一遍 pop_front 的内部实现：

```rust ,ignore
// Bring the Box back to life so we can move out its value and
// Drop it (Box continues to magically understand this for us).
let boxed_node = Box::from_raw(node.as_ptr());
let result = boxed_node.elem;

// Make the next node into the new front.
self.front = boxed_node.back;
if let Some(new) = self.front {
    // Cleanup its reference to the removed node
    (*new.as_ptr()).front = None;
} else {
    // If the front is now null, then this list is now empty!
    debug_assert!(self.len == 1);
    self.back = None;
}

self.len -= 1;
result
// Box gets implicitly freed here, knows there is no T.
```

你看出那个 bug 了吗？可怕的是，它其实就是这一行：

```rust ,ignore
debug_assert!(self.len == 1);
```

*真的假的*？我们那个用于测试的完整性检查居然是个 bug？？是的！！！嗯，如果我们把集合实现对了，它*本不该*是；但它能把“哦我们没把 len 维护好”这种无伤大雅的问题，变成*一个可被利用的内存安全漏洞*！为什么？因为它会 panic！大多数时候你不必去想、也不必担心 panic，可一旦你开始写*真正*不安全的代码、并且对“不变式”马马虎虎起来，你就必须对 panic 高度警觉！

我们得聊聊[*异常安全性*](https://doc.rust-lang.org/nightly/nomicon/exception-safety.html)（也叫 panic 安全性，也叫展开安全性，等等）。

事情是这样的：默认情况下，panic 会进行*展开*。展开不过是“让每一个函数立刻返回”的一种花哨说法。你可能会想“嗯，如果*所有人*都返回了，那程序马上就要死了，那还操心它干嘛？”，但你想错了！

我们必须操心它，原因有两个：函数返回时析构函数会运行，而且展开是可以被*捕获*的。这两种情况下，代码都可能在 panic 之后继续运行，所以我们必须非常小心，确保在任何可能发生 panic 的时刻，我们的不安全集合都处于*某种*自洽的状态，因为每一次 panic 都是一次隐式的提前返回！

我们来想想，当执行到那一行时，我们的集合处于什么状态：

我们的 boxed_node 在栈上，而且我们已经把元素从中取出来了。如果我们在这时返回，那个 Box 就会被丢弃，节点也会被释放。现在你看出来了吗……？self.back 仍然指着那个已被释放的节点！等我们把集合的其余部分实现出来、开始用 self.back 干事情时，这就会导致释放后使用！哎呀！

有意思的是，这一行也有类似的问题，但它安全得多：

```rust ,ignore
self.len -= 1;
```

在 debug 构建中，Rust 默认会检查下溢和上溢，并在发生时 panic。没错，每一个算术运算都是一处 panic 安全隐患！这一处*要好一些*，因为它发生在我们已经修复好所有不变式之后，所以不会造成内存安全问题……只要我们不信任 len 是对的；不过话说回来，如果它下溢了，那它肯定就是错的，所以横竖我们都完蛋了！从某种意义上说，那个 debug 断言*更糟*，因为它能把一个小问题升级成一个致命问题！

我已经提了好几次“不变式”这个词，那是因为它对 panic 安全性来说是个非常有用的概念！基本上，在我们集合的外部观察者看来，有某些性质是我们始终在维持的。对 LinkedList 来说，其中之一就是：链表中任何可达的节点都仍然处于已分配、已初始化的状态。

在实现的*内部*，我们有更多的余地*临时*打破不变式，只要我们确保*在任何人注意到之前*把它们修好。这其实正是 Rust 的所有权与借用系统对集合而言的“杀手级应用”之一：如果某个操作需要`&mut Self`，那我们就*被保证*拥有对集合的独占访问权，于是临时打破不变式是没问题的，因为我们心里有底，没人能偷偷摸摸地动它。

这一点也许最极致的体现是 [Vec::drain](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.drain)，它实际上允许你彻底砸碎 Vec 的一条核心不变式，从 Vec 的*前端*、甚至*中间*开始把值移走。它之所以*可靠*，是因为我们返回的 Drain 迭代器持有一个指向 Vec 的`&mut`，因此一切访问都被它把持着！在 Drain 迭代器消失之前，没人能观察到那个 Vec；而在它消失时，它的析构函数就能在任何人察觉之前把 Vec“修好”，这真是完美——

[它并不完美](https://doc.rust-lang.org/nightly/nomicon/leaking.html#drain)。不幸的是，你[不能指望自己无法控制的代码中的析构函数一定会运行](https://doc.rust-lang.org/std/mem/fn.forget.html)，所以即便有了 Drain，我们仍需额外做点工作，让我们的类型始终维持不变式，只不过方式有点滑稽：[我们在一开始就把 Vec 的 len 设成 0](https://doc.rust-lang.org/std/mem/fn.forget.html)，这样如果有人泄漏了 Drain，他们得到的将是一个*安全*的 Vec……只不过还丢了一堆数据。你泄漏我？那我就泄漏你！以眼还眼！真正的正义！

至于那种你*确实可以*用析构函数来保证 panic 安全性的情形，可以看看 [BinaryHeap::sift_up 的案例分析](https://doc.rust-lang.org/nightly/nomicon/exception-safety.html#binaryheapsift_up)。

总之，我们的 LinkedList 用不上这些花哨的东西，我们只需要对以下几点更警觉一些：在哪里打破了不变式、我们信任／要求什么是正确的，以及避免在棘手任务的中途引入不必要的展开。

在这个例子里，我们有两个选项可以让代码更稳健一些：

* 更积极地使用 Option::take 之类的操作，因为它们更具“事务性”，倾向于保持不变式。

* 干掉那些 debug_assert，并相信我们自己能写出更好的测试，配上专门的、永远不会在用户代码中运行的“完整性检查”函数。

原则上我喜欢第一个选项，但它对双向链表其实效果不佳，因为所有东西都被双重冗余地编码了。Option::take 在这里解决不了问题，倒是把那个 debug_assert 往下挪一行就能解决。不过说真的，何必给自己添堵？我们干脆把那些 debug_assert 删掉，并确保任何可能 panic 的东西都位于方法的开头或结尾，在那里我们的不变式应当是已知成立的。

（这样说来，把它们看作*前置条件*和*后置条件*也许更准确，不过你真的应该尽最大努力把它们当作不变式来对待！）

这是我们现在的完整实现：

```rust
use std::ptr::NonNull;
use std::marker::PhantomData;

pub struct LinkedList<T> {
    front: Link<T>,
    back: Link<T>,
    len: usize,
    _boo: PhantomData<T>,
}

type Link<T> = Option<NonNull<Node<T>>>;

struct Node<T> {
    front: Link<T>,
    back: Link<T>,
    elem: T, 
}

impl<T> LinkedList<T> {
    pub fn new() -> Self {
        Self {
            front: None,
            back: None,
            len: 0,
            _boo: PhantomData,
        }
    }

    pub fn push_front(&mut self, elem: T) {
        // SAFETY: it's a linked-list, what do you want?
        unsafe {
            let new = NonNull::new_unchecked(Box::into_raw(Box::new(Node {
                front: None,
                back: None,
                elem,
            })));
            if let Some(old) = self.front {
                // Put the new front before the old one
                (*old.as_ptr()).front = Some(new);
                (*new.as_ptr()).back = Some(old);
            } else {
                // If there's no front, then we're the empty list and need 
                // to set the back too.
                self.back = Some(new);
            }
            // These things always happen!
            self.front = Some(new);
            self.len += 1;
        }
    }

    pub fn pop_front(&mut self) -> Option<T> {
        unsafe {
            // Only have to do stuff if there is a front node to pop.
            self.front.map(|node| {
                // Bring the Box back to life so we can move out its value and
                // Drop it (Box continues to magically understand this for us).
                let boxed_node = Box::from_raw(node.as_ptr());
                let result = boxed_node.elem;

                // Make the next node into the new front.
                self.front = boxed_node.back;
                if let Some(new) = self.front {
                    // Cleanup its reference to the removed node
                    (*new.as_ptr()).front = None;
                } else {
                    // If the front is now null, then this list is now empty!
                    self.back = None;
                }

                self.len -= 1;
                result
                // Box gets implicitly freed here, knows there is no T.
            })
        }
    }

    pub fn len(&self) -> usize {
        self.len
    }
}
```

这里有什么会 panic 呢？嗯，老实说要知道这一点，你得算半个 Rust 专家，不过谢天谢地，我就是！

在这段代码里，我能看到*可能*会 panic 的地方只有`Box::new`（在内存不足的情况下）和 len 的算术运算（除非有人干出那种把标准库开着 debug_assert 重新编译的绝顶离谱操作，但这是你永远不该做的事）。所有这些东西都位于我们方法的最末尾或最开头，所以没错，我们既漂亮又安全！

……`Box::new`会 panic 这件事让你意外了吗？panic 就是会这么阴你！努力维持好那些不变式，这样你就不用操心它了！

