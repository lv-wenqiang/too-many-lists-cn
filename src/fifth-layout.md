# 布局

那么单向链表队列长什么样呢？回想一下，我们做单向链表栈的时候，是从链表的一端
压入，再从同一端弹出。栈和队列之间唯一的区别在于，队列是从*另一*端弹出的。
所以从栈的实现出发，我们有：

```text
input list:
[Some(ptr)] -> (A, Some(ptr)) -> (B, None)

stack push X:
[Some(ptr)] -> (X, Some(ptr)) -> (A, Some(ptr)) -> (B, None)

stack pop:
[Some(ptr)] -> (A, Some(ptr)) -> (B, None)
```

要做出一个队列，我们只需要决定把哪个操作挪到链表的末端：push 还是 pop？
因为我们的链表是单向的，把*任意一个*操作挪到末端所需的工夫其实是一样的。

要把`push`挪到末端，我们只要一路走到那个`None`，把它设成装着新元素的 Some。

```text
input list:
[Some(ptr)] -> (A, Some(ptr)) -> (B, None)

flipped push X:
[Some(ptr)] -> (A, Some(ptr)) -> (B, Some(ptr)) -> (X, None)
```

要把`pop`挪到末端，我们只要一路走到 None *之前*的那个节点，然后把它`take`走：

```text
input list:
[Some(ptr)] -> (A, Some(ptr)) -> (B, Some(ptr)) -> (X, None)

flipped pop:
[Some(ptr)] -> (A, Some(ptr)) -> (B, None)
```

我们今天就可以这么干然后收工，但那也太糟糕了！这两个操作都要走遍*整个*链表。
有人会争辩说，这样的队列实现确实算队列，因为它暴露了正确的接口。然而我认为
性能保证也是接口的一部分。我不在乎精确的渐进界，只在乎“快”和“慢”。
队列保证 push 和 pop 是快的，而走遍整个链表绝对*不*快。

一个关键的观察是：我们在一遍又一遍地做*同一件事*，浪费了大量的工作。
我们能不能把这些工作“缓存”下来重复利用？当然可以！我们可以存一个指向链表末端的
指针，然后直接跳过去！

事实证明，push 和 pop 这两种颠倒方式里只有一种行得通。要颠倒`pop`，
我们就得把“尾”指针往回移，可因为我们的链表是单向的，这件事没法高效地做到。
如果改为颠倒`push`，我们只需要把“头”指针往前移，这就容易了。

来试试看：

```rust ,ignore
use std::mem;

pub struct List<T> {
    head: Link<T>,
    tail: Link<T>, // NEW!
}

type Link<T> = Option<Box<Node<T>>>;

struct Node<T> {
    elem: T,
    next: Link<T>,
}

impl<T> List<T> {
    pub fn new() -> Self {
        List { head: None, tail: None }
    }

    pub fn push(&mut self, elem: T) {
        let new_tail = Box::new(Node {
            elem: elem,
            // When you push onto the tail, your next is always None
            next: None,
        });

        // swap the old tail to point to the new tail
        let old_tail = mem::replace(&mut self.tail, Some(new_tail));

        match old_tail {
            Some(mut old_tail) => {
                // If the old tail existed, update it to point to the new tail
                old_tail.next = Some(new_tail);
            }
            None => {
                // Otherwise, update the head to point to it
                self.head = Some(new_tail);
            }
        }
    }
}
```

现在实现细节我会讲得快一些，因为这类事情我们应该已经挺熟悉了。这并不是说你
第一次写就该写出这样的代码。我只是跳过了一些我们以前必须应付的试错过程。
其实我写这段代码时犯了一大堆错误，只是没展示出来；不过看我漏掉`mut`或者`;`
看多了也就没什么教育意义了。别担心，我们还会见到大量*别的*错误信息！

```text
> cargo build

error[E0382]: use of moved value: `new_tail`
  --> src/fifth.rs:38:38
   |
26 |         let new_tail = Box::new(Node {
   |             -------- move occurs because `new_tail` has type `std::boxed::Box<fifth::Node<T>>`, which does not implement the `Copy` trait
...
33 |         let old_tail = mem::replace(&mut self.tail, Some(new_tail));
   |                                                          -------- value moved here
...
38 |                 old_tail.next = Some(new_tail);
   |                                      ^^^^^^^^ value used here after move
```

糟了！

> use of moved value: `new_tail`

Box 没有实现 Copy，所以我们不能把它同时赋给两个地方。更重要的是，Box *拥有*
它所指向的东西，并且会在被丢弃时试图释放它。如果我们的`push`实现编译通过了，
那我们就会把链表的尾部重复释放两次！实际上，照现在这个写法，我们的代码会在
每次 push 时都释放掉 old_tail。哎呀！🙀

好吧，我们知道怎么造一个不拥有所有权的指针。那不就是引用嘛！

```rust ,ignore
pub struct List<T> {
    head: Link<T>,
    tail: Option<&mut Node<T>>, // NEW!
}

type Link<T> = Option<Box<Node<T>>>;

struct Node<T> {
    elem: T,
    next: Link<T>,
}

impl<T> List<T> {
    pub fn new() -> Self {
        List { head: None, tail: None }
    }

    pub fn push(&mut self, elem: T) {
        let new_tail = Box::new(Node {
            elem: elem,
            // When you push onto the tail, your next is always None
            next: None,
        });

        // Put the box in the right place, and then grab a reference to its Node
        let new_tail = match self.tail.take() {
            Some(old_tail) => {
                // If the old tail existed, update it to point to the new tail
                old_tail.next = Some(new_tail);
                old_tail.next.as_deref_mut()
            }
            None => {
                // Otherwise, update the head to point to it
                self.head = Some(new_tail);
                self.head.as_deref_mut()
            }
        };

        self.tail = new_tail;
    }
}
```

这里没什么太玄乎的。基本思路和之前的代码一样，只不过我们利用了隐式返回的便利，
从我们塞放真正 Box 的地方把尾部引用提取出来。

```text
> cargo build

error[E0106]: missing lifetime specifier
 --> src/fifth.rs:3:18
  |
3 |     tail: Option<&mut Node<T>>, // NEW!
  |                  ^ expected lifetime parameter
```

哦对，我们得给类型里的引用加上生命周期。嗯……这个引用的生命周期是什么呢？
这看起来挺像 IterMut 的，对吧？那就照我们对 IterMut 的做法来，加一个泛型的`'a`：

```rust ,ignore
pub struct List<'a, T> {
    head: Link<T>,
    tail: Option<&'a mut Node<T>>, // NEW!
}

type Link<T> = Option<Box<Node<T>>>;

struct Node<T> {
    elem: T,
    next: Link<T>,
}

impl<'a, T> List<'a, T> {
    pub fn new() -> Self {
        List { head: None, tail: None }
    }

    pub fn push(&mut self, elem: T) {
        let new_tail = Box::new(Node {
            elem: elem,
            // When you push onto the tail, your next is always None
            next: None,
        });

        // Put the box in the right place, and then grab a reference to its Node
        let new_tail = match self.tail.take() {
            Some(old_tail) => {
                // If the old tail existed, update it to point to the new tail
                old_tail.next = Some(new_tail);
                old_tail.next.as_deref_mut()
            }
            None => {
                // Otherwise, update the head to point to it
                self.head = Some(new_tail);
                self.head.as_deref_mut()
            }
        };

        self.tail = new_tail;
    }
}
```

```text
cargo build

error[E0495]: cannot infer an appropriate lifetime for autoref due to conflicting requirements
  --> src/fifth.rs:35:27
   |
35 |                 self.head.as_deref_mut()
   |                           ^^^^^^^^^^^^
   |
note: first, the lifetime cannot outlive the anonymous lifetime #1 defined on the method body at 18:5...
  --> src/fifth.rs:18:5
   |
18 | /     pub fn push(&mut self, elem: T) {
19 | |         let new_tail = Box::new(Node {
20 | |             elem: elem,
21 | |             // When you push onto the tail, your next is always None
...  |
39 | |         self.tail = new_tail;
40 | |     }
   | |_____^
note: ...so that reference does not outlive borrowed content
  --> src/fifth.rs:35:17
   |
35 |                 self.head.as_deref_mut()
   |                 ^^^^^^^^^
note: but, the lifetime must be valid for the lifetime 'a as defined on the impl at 13:6...
  --> src/fifth.rs:13:6
   |
13 | impl<'a, T> List<'a, T> {
   |      ^^
   = note: ...so that the expression is assignable:
           expected std::option::Option<&'a mut fifth::Node<T>>
              found std::option::Option<&mut fifth::Node<T>>


```

哇，这错误信息真是详细。这有点让人不安，因为它暗示我们干了某件相当离谱的事。
这里有一段很有意思：

> the lifetime must be valid for the lifetime `'a` as defined on the impl

我们是从`self`借用的，而编译器希望我们能活得和`'a`一样久，
那如果我们告诉它`self`*确实*能活那么久呢……？

```rust ,ignore
    pub fn push(&'a mut self, elem: T) {
```

```text
cargo build

warning: field is never used: `elem`
 --> src/fifth.rs:9:5
  |
9 |     elem: T,
  |     ^^^^^^^
  |
  = note: #[warn(dead_code)] on by default
```

哦，嘿，成了！太好了！

顺手把`pop`也写了：

```rust ,ignore
pub fn pop(&'a mut self) -> Option<T> {
    // Grab the list's current head
    self.head.take().map(|head| {
        let head = *head;
        self.head = head.next;

        // If we're out of `head`, make sure to set the tail to `None`.
        if self.head.is_none() {
            self.tail = None;
        }

        head.elem
    })
}
```

再给它写个简单的测试：

```rust ,ignore
#[cfg(test)]
mod test {
    use super::List;
    #[test]
    fn basics() {
        let mut list = List::new();

        // Check empty list behaves right
        assert_eq!(list.pop(), None);

        // Populate list
        list.push(1);
        list.push(2);
        list.push(3);

        // Check normal removal
        assert_eq!(list.pop(), Some(1));
        assert_eq!(list.pop(), Some(2));

        // Push some more just to make sure nothing's corrupted
        list.push(4);
        list.push(5);

        // Check normal removal
        assert_eq!(list.pop(), Some(3));
        assert_eq!(list.pop(), Some(4));

        // Check exhaustion
        assert_eq!(list.pop(), Some(5));
        assert_eq!(list.pop(), None);
    }
}
```

```text
cargo test

error[E0499]: cannot borrow `list` as mutable more than once at a time
  --> src/fifth.rs:68:9
   |
65 |         assert_eq!(list.pop(), None);
   |                    ---- first mutable borrow occurs here
...
68 |         list.push(1);
   |         ^^^^
   |         |
   |         second mutable borrow occurs here
   |         first borrow later used here

error[E0499]: cannot borrow `list` as mutable more than once at a time
  --> src/fifth.rs:69:9
   |
65 |         assert_eq!(list.pop(), None);
   |                    ---- first mutable borrow occurs here
...
69 |         list.push(2);
   |         ^^^^
   |         |
   |         second mutable borrow occurs here
   |         first borrow later used here

error[E0499]: cannot borrow `list` as mutable more than once at a time
  --> src/fifth.rs:70:9
   |
65 |         assert_eq!(list.pop(), None);
   |                    ---- first mutable borrow occurs here
...
70 |         list.push(3);
   |         ^^^^
   |         |
   |         second mutable borrow occurs here
   |         first borrow later used here


....

** WAY MORE LINES OF ERRORS **

....

error: aborting due to 11 previous errors
```

🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀🙀

我的老天爷。

编译器冲我们狂吐一通并没有错。我们刚刚犯下了 Rust 的一条大忌：
我们把一个指向自己的引用存进了*自己内部*。不知怎么的，我们居然在`push`和`pop`
的实现里说服了 Rust 这完全说得通（我们能做到这点让我着实震惊）。

这之所以*看起来*行得通，是因为 Rust 其实压根没有“指向自身的指针”这个概念。
代码的每一部分单独看*在技术上*都是正确的（我们*可以*调用一次 push 和 pop），
但接着我们所造之物的荒谬性就发作了，一切都彻底*卡死*。

我相信我们写出来的东西*总有*些用处，但就*我*而言，它不过是语法上合法的*胡言乱语*。
我们说自己包含着某个生命周期为`'a`的东西，而且`push`和`pop`会以那个生命周期
借用*self*。这*很怪*，但 Rust 可以*逐个*审视我们代码的每一部分，
并且看不出有任何规则被打破。

可是一旦我们真的试着*使用*这个链表，编译器马上就会说“没错，你已经以`'a`
可变地借用了`self`，所以在`'a`结束之前你不能再用`self`了”，
而*同时*又说“因为你包含着`'a`，它必须在整个链表存在期间都保持有效”。

这*几乎*就是个矛盾，但确实*有*一个解法：只要你一`push`或者`pop`，
这个链表就把自己“钉”在原地，再也无法被访问。它吞下了自己那条众所周知的尾巴，
升入了梦境之国。

> **旁白**：这本书刚写的时候它还不存在，不过 Rust 后来真的
> [把*钉住*（pin）这个概念形式化成了有用的东西][pin]！
> 这大概是自*借用检查器*以来这门语言最复杂的一项新增特性。
> 不过我们*并不想*让我们的链表被钉住！
>
> Pin 对 async-await／future／协程来说*确实*是必要而有用的，因为编译器需要
> 能把一个函数的所有局部变量打包成某种结构体，存到某个地方，
> 直到那个 future／协程准备好被恢复执行。既然局部变量可以引用其他局部变量，
> 而我们又希望这件事*能行得通*，那么这些结构体最终就可能包含指向自身的引用！
>
> 所以为了`await`或`yield`，Rust 需要一种能够正确描述和操作被钉住的值的办法。
> 谢天谢地，这一整套东西*基本上*都被藏进了编译器的自动机制里，
> 正常情况下没人真的需要去想`Pin`（甚至连*Future*都不用想）。主要的例外是，
> 这些东西对那些构建和设计 tokio 之类 async *运行时*的人来说非常重要。
>
> 我们不会在本书中实现一个 async 运行时。我知道我的朋友们懂各种能用`Pin`
> 玩出来的“酷炫”（离谱）*花招*，但据我看来，我还是不知道为妙。
> 我会继续告诉自己：被钉住的类型不是真的，它们伤害不了我。

我们的`pop`实现暗示了为什么把指向自身的引用存进*自己内部*会非常危险：

```rust ,ignore
// ...
if self.head.is_none() {
    self.tail = None;
}
```

要是我们忘了这么做呢？那我们的尾指针就会指向某个*已经被从链表中移除*的节点。
这样的节点会立刻被释放，于是我们就有了一个悬垂指针——而 Rust 本该保护我们
不受其害才对！

而 Rust 确实正在保护我们免于那种危险。只不过是以一种非常……
**绕弯子**的方式。

那我们能怎么办？回到`Rc<RefCell>>`的地狱里去？

求你了。别。

不，我们要改为脱轨行驶，使用*原始指针*。
我们的布局会长这样：

```rust ,ignore
pub struct List<T> {
    head: Link<T>,
    tail: *mut Node<T>, // DANGER DANGER
}

type Link<T> = Option<Box<Node<T>>>;

struct Node<T> {
    elem: T,
    next: Link<T>,
}
```


就这样。再没有那些窝囊的引用计数、动态借用检查之类的破事了！
真真正正、硬邦邦、不受检查的指针。

> **旁白：**这个实现事实上依然危险地错着，只是还没到学这一课的时候。下一节会一如既往地以惨痛的方式学到它。

大伙儿，我们来当 C 吧。整天都当 C。

我到家了。我准备好了。

你好，`unsafe`。

> **旁白：**哇，作者在这儿真是狂妄到了极点。


[pin]: https://doc.rust-lang.org/std/pin/index.html
