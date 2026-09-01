# 布局与基础 2：动真格的原始指针

> 前三节的太长不看版：把`&`、`&mut`、`Box`这类安全指针和`*mut`、`*const`这类不安全指针随意混用，是引发未定义行为的配方，因为安全指针引入了额外的约束，而我们用原始指针时并没有遵守它们。

老天我又得写链表了。行吧。行。没事的。我们没事。

这一节我们会飞快地推进一大截，因为第一次尝试时我们已经讨论过设计了，而且除了把安全指针和不安全指针混在一起这一点之外，我们当时做的一切*基本上*都是对的。


# 布局

所以在新的布局里，我们将只使用原始指针，一切都会完美无缺，我们再也不会犯错了。

这是我们原来那个坏掉的布局：

```rust
pub struct List<T> {
    head: Link<T>,
    tail: *mut Node<T>, // INNOCENT AND KIND
}

type Link<T> = Option<Box<Node<T>>>; // THE REAL EVIL

struct Node<T> {
    elem: T,
    next: Link<T>,
}
```

而这是我们的新布局：

```rust
pub struct List<T> {
    head: Link<T>,
    tail: *mut Node<T>,
}

type Link<T> = *mut Node<T>; // MUCH BETTER

struct Node<T> {
    elem: T,
    next: Link<T>,
}
```

记住：在使用原始指针时，Option 就没那么好用、那么有价值了，所以我们不再用它。后面的章节里我们会看看`NonNull`类型，不过现在先别操心这个。



# 基础

List::new 基本上没变。

```rust ,ignore
use ptr;

impl<T> List<T> {
    pub fn new() -> Self {
        List { head: ptr::null_mut(), tail: ptr::null_mut() }
    }
}
```

Push 基本上也是一——


```rust ,ignore
pub fn push(&mut self, elem: T) {
    let mut new_tail = Box::new(
```

等等，我们不再用 Box 了。不用 Box 我们该怎么分配内存？

嗯，我们*可以*用`std::alloc::alloc`，但那就像把武士刀带进厨房。活儿是能干成，可有点杀鸡用牛刀，还很不趁手。

我们想要*有*box，但又*不要*。有一个完全离谱、但*也许*可行的选项是这样做：

```
struct Node<T> {
    elem: T,
    real_next: Option<Box<Node<T>>>,
    next: *mut Node<T>,
}
```

思路是：我们创建 Box 并把它们存在节点里，然后取出指向它们的原始指针，在用完这个 Node、想要销毁它之前都只使用那个原始指针。到那时我们就可以把 Box 从`real_next`里`take`出来并丢弃它。我*觉得*这符合我们那套非常简化的堆叠借用模型？

你要是想试着这么搞，那就“玩得开心”，可这看着实在糟糕，对吧？这又不是讲 Rc 和 RefCell 的那一章，我们不玩这套*游戏*了。我们要做的是简单干净的东西。

所以我们改用非常好用的 [Box::into_raw][] 函数：

> ```rust ,ignore
>   pub fn into_raw(b: Box<T>) -> *mut T
> ```
>
> 消耗掉这个 Box，返回一个被包装过的原始指针。
>
> 该指针将是正确对齐且非空的。
>
>调用此函数之后，先前由 Box 管理的那块内存就由调用者负责了。具体来说，调用者应当正确地销毁 T 并释放内存，同时考虑到 Box 所使用的内存布局。做到这一点最简单的办法，是用`Box::from_raw`函数把原始指针转换回 Box，让 Box 的析构函数去完成清理工作。
>
> 注意：这是一个关联函数，也就是说你必须写成`Box::into_raw(b)`而不是`b.into_raw()`。这样做是为了不与内部类型上的方法冲突。
>
> **示例**
>
> 用 Box::from_raw 把原始指针转换回 Box 以实现自动清理：
>
> ```
>  let x = Box::new(String::from("Hello"));
>  let ptr = Box::into_raw(x);
>  let x = unsafe { Box::from_raw(ptr) };
> ```

漂亮，这看起来*简直就是*为我们的用例设计的。它也符合我们试图遵守的规则：从安全的东西开始，转换成原始指针，然后只在最后（当我们想要 Drop 它时）再转换回安全的东西。

这基本上就和前面那个古怪的`real_next`做法一模一样，只是不用再折腾着去存一个 Box——反正它和那个原始指针是同一个指针。

另外，既然我们现在到处都只用原始指针了，那就别再操心把`unsafe`块划得多窄了：现在全都是 unsafe。（其实一直都是，不过有时候骗骗自己也挺好。）


```rust ,ignore
pub fn push(&mut self, elem: T) {
    unsafe {
        // Immediately convert the Box into a raw pointer
        let new_tail = Box::into_raw(Box::new(Node {
            elem: elem,
            next: ptr::null_mut(),
        }));

        if !self.tail.is_null() {
            (*self.tail).next = new_tail;
        } else {
            self.head = new_tail;
        }

        self.tail = new_tail;
    }
}
```


嘿，既然我们坚持只用原始指针，这段代码现在看起来干净多了！

接着是 pop，它也和我们当初留下的样子相当接近，不过我们得记得用`Box::from_raw`来清理那块分配：

```rust ,ignore
pub fn pop(&mut self) -> Option<T> {
    unsafe {
        if self.head.is_null() {
            None
        } else {
            // RISE FROM THE GRAVE
            let head = Box::from_raw(self.head);
            self.head = head.next;

            if self.head.is_null() {
                self.tail = ptr::null_mut();
            }

            Some(head.elem)
        }
    }
}
```

我们那些漂亮的小`take`和`map`都没了，现在只能手动检查和设置`null`了。

趁着还在这儿，我们把析构函数也塞进去。这一次我们就把它实现成不停地 pop，因为这样既可爱又简单：

```rust ,ignore
impl<T> Drop for List<T> {
    fn drop(&mut self) {
        while let Some(_) = self.pop() { }
    }
}
```


好了，见证真相的时刻：

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

        // Check the exhaustion case fixed the pointer right
        list.push(6);
        list.push(7);

        // Check normal removal
        assert_eq!(list.pop(), Some(6));
        assert_eq!(list.pop(), Some(7));
        assert_eq!(list.pop(), None);
    }
}
```

```text
cargo test

running 12 tests
test fifth::test::basics ... ok
test first::test::basics ... ok
test fourth::test::basics ... ok
test fourth::test::peek ... ok
test second::test::basics ... ok
test fourth::test::into_iter ... ok
test second::test::into_iter ... ok
test second::test::iter ... ok
test second::test::iter_mut ... ok
test second::test::peek ... ok
test third::test::basics ... ok
test third::test::iter ... ok

test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured
```

很好，可是 miri 同意吗？

```text
MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri test

running 12 tests
test fifth::test::basics ... ok
test first::test::basics ... ok
test fourth::test::basics ... ok
test fourth::test::peek ... ok
test second::test::basics ... ok
test fourth::test::into_iter ... ok
test second::test::into_iter ... ok
test second::test::iter ... ok
test second::test::iter_mut ... ok
test second::test::peek ... ok
test third::test::basics ... ok
test third::test::iter ... ok

test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured
```

耶！！！！！

它真的成了！

大概吧！

没能找到未定义行为并不能证明它不在那儿等着搞事情，但我为一本讲链表的搞笑书所愿意付出的严谨程度是有限的，所以我们就把这称作 100% 机器验证过的证明，谁有意见谁去嘬我的 COQ！

∴ QED □


[Box::into_raw]: https://doc.rust-lang.org/std/boxed/struct.Box.html#method.into_raw
