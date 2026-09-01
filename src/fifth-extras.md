# 额外的零碎

既然`push`和`pop`都写好了，说来奇怪，其余一切其实和栈的情形完全相同。只有那些会改变链表长度的操作才需要动到尾指针。

当然啦，既然现在一切都是不安全指针了，我们就得重写代码来使用它们！而且既然我们要把所有代码都过一遍，不如趁机确认一下有没有漏掉什么。

总之，我们先开始从栈的实现里复制粘贴代码：

```rust ,ignore
// ...

pub struct IntoIter<T>(List<T>);

pub struct Iter<'a, T> {
    next: Option<&'a Node<T>>,
}

pub struct IterMut<'a, T> {
    next: Option<&'a mut Node<T>>,
}
```

IntoIter 看起来没问题，但`Iter`和`IterMut`违反了我们“类型里不再使用安全指针”的简单规则。保险起见，我们把它们改成用原始指针：

```rust ,ignore
pub struct IntoIter<T>(List<T>);

pub struct Iter<'a, T> {
    next: *mut Node<T>,
}

pub struct IterMut<'a, T> {
    next: *mut Node<T>,
}

impl<T> List<T> {
    pub fn into_iter(self) -> IntoIter<T> {
        IntoIter(self)
    }

    pub fn iter(&self) -> Iter<'_, T> {
        Iter { next: self.head }
    }

    pub fn iter_mut(&mut self) -> IterMut<'_, T> {
        IterMut { next: self.head }
    }
}
```

看起来不错！

```text
error[E0392]: parameter `'a` is never used
  --> src\fifth.rs:17:17
   |
17 | pub struct Iter<'a, T> {
   |                 ^^ unused parameter
   |
   = help: consider removing `'a`, referring to it in a field, 
     or using a marker such as `PhantomData`

error[E0392]: parameter `'a` is never used
  --> src\fifth.rs:21:20
   |
21 | pub struct IterMut<'a, T> {
   |                    ^^ unused parameter
   |
   = help: consider removing `'a`, referring to it in a field, 
     or using a marker such as `PhantomData`
```

看起来不妙！它们念叨的这个 [PhantomData](https://doc.rust-lang.org/std/marker/struct.PhantomData.html) 是什么东西？

> 零大小类型，用来标记那些“表现得像是”拥有一个`T`的东西。
>
> 给你的类型加上一个`PhantomData<T>`字段，就是在告诉编译器：你的类型表现得就像它存储了一个`T`类型的值，尽管实际上并没有。在计算某些安全性属性时会用到这一信息。
>
> 关于如何使用`PhantomData<T>`的更深入解释，请参见[死灵书](https://doc.rust-lang.org/nightly/nomicon/)。

嘿别急着跑题，我们读的是*我*写的书。可不是某个大*书呆子*写的那另一本！我敢打赌他们要是在那书里写个数据结构，肯定是数组栈之类的逊玩意儿，*才不是*链表。

> 未被使用的生命周期参数
>
> PhantomData 也许最常见的用例，就是某个结构体带有一个未被使用的生命周期参数，通常是某段不安全代码的一部分。

啊，所以我们在类型里命名了一个生命周期，却没有真正使用它。我们*可以*走 PhantomData 这条路，但我想把它留给下一章的双向链表，那里*真的*会需要它。

我们的处境挺有意思，其实我们并不需要 PhantomData。*我觉得*。我就这么断言了，并且相信它是真的；如果最后 miri 冲我们吼，我就认输，我们再去搞 PhantomData 那一套。

我们实际要做的，是把引用放回这些迭代器类型里，并为还能在某些地方用上引用而高兴。我认为这是站得住脚的，因为使用迭代器时仍然存在一种恰当的嵌套：你创建迭代器，用一阵子安全引用，然后丢弃这个迭代器。

只有在迭代器消失之后，你才能访问链表并调用`push`、`pop`这类需要摆弄尾指针和 Box 的东西。当然，在迭代过程中我们*确实*会解引用一堆原始指针，所以那里是有某种混用的，不过我们应该可以把那些引用看作是对不安全指针的重借用。

*我*自己都没有百分百被说服，但我就想试一把看看！

```rust ,ignore
pub struct IntoIter<T>(List<T>);

pub struct Iter<'a, T> {
    next: Option<&'a Node<T>>,
}

pub struct IterMut<'a, T> {
    next: Option<&'a mut Node<T>>,
}

impl<T> List<T> {
    pub fn into_iter(self) -> IntoIter<T> {
        IntoIter(self)
    }

    pub fn iter(&self) -> Iter<'_, T> {
        unsafe {
            Iter { next: self.head.as_ref() }
        }
    }

    pub fn iter_mut(&mut self) -> IterMut<'_, T> {
        unsafe {
            IterMut { next: self.head.as_mut() }
        }
    }
}
```

如果我们要存引用，就需要把原始指针升级成“引用的 Option”。我们*可以*去检查指针是不是空的，但这正是那种极其狭窄的情形之一——我*认为*在这里用那两个讨厌的方法 [ptr::as_ref](https://doc.rust-lang.org/std/primitive.pointer.html#method.as_ref-1) 和 [ptr::as_mut](https://doc.rust-lang.org/std/primitive.pointer.html#method.as_mut) 是可以的。

我*通常*建议像躲瘟疫一样躲开这些方法，因为它们会干出一些出人意料的恶心事，而且它们本质上就是在重新引入引用——而我那条“简单规则”的全部内容就是别这么干！

这些方法附带了一大堆警告，其中最有意思的是这条：

> 你必须自行强制遵守 Rust 的别名规则，因为返回的生命周期`'a`是任意选定的，未必反映数据的实际生命周期。具体来说，在这个生命周期期间，该指针所指向的内存不得通过任何其他指针被访问（读或写）。

嘿看，这不就是我们聊了 25 页的那玩意儿嘛！我已经断言过我们在这里用引用*肯定*没问题，所以别名问题解决！另一处邪恶的地方在于它的签名：

```rust ,ignore
pub unsafe fn as_mut<'a>(self) -> Option<&'a mut T>
```

你看到那个生命周期压根没和输入挂钩了吗，因为`self`是按值传的？没错，这就是我们所说的“无界生命周期”，是个恶心玩意儿。你要它多大，它就愿意假装自己有多大，连`'static`都行！*对付*它的办法，是把它放到一个*有界*的地方，通常也就是“尽快把它从函数里返回出去，好让函数签名限制住它”。

老天我对此很紧张，但我们还是要硬着头皮往前推！我们从栈那边偷几个迭代器实现过来：

```rust ,ignore
impl<T> Iterator for IntoIter<T> {
    type Item = T;
    fn next(&mut self) -> Option<Self::Item> {
        self.0.pop()
    }
}

impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;

    fn next(&mut self) -> Option<Self::Item> {
        unsafe {
            self.next.map(|node| {
                self.next = node.next.as_ref();
                &node.elem
            })
        }
    }
}

impl<'a, T> Iterator for IterMut<'a, T> {
    type Item = &'a mut T;

    fn next(&mut self) -> Option<Self::Item> {
        unsafe {
            self.next.take().map(|node| {
                self.next = node.next.as_mut();
                &mut node.elem
            })
        }
    }
}
```

见证真相的时刻……

```text
cargo test

running 15 tests
test fifth::test::basics ... ok
test fifth::test::into_iter ... ok
test fifth::test::iter ... ok
test fifth::test::iter_mut ... ok
test first::test::basics ... ok
test fourth::test::basics ... ok
test fourth::test::into_iter ... ok
test fourth::test::peek ... ok
test second::test::basics ... ok
test second::test::into_iter ... ok
test second::test::iter ... ok
test second::test::iter_mut ... ok
test second::test::peek ... ok
test third::test::iter ... ok
test third::test::basics ... ok

test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;
```

```text
MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri test

running 15 tests
test fifth::test::basics ... ok
test fifth::test::into_iter ... ok
test fifth::test::iter ... ok
test fifth::test::iter_mut ... ok
test first::test::basics ... ok
test fourth::test::basics ... ok
test fourth::test::into_iter ... ok
test fourth::test::peek ... ok
test second::test::basics ... ok
test second::test::into_iter ... ok
test second::test::iter ... ok
test second::test::iter_mut ... ok
test second::test::peek ... ok
test third::test::basics ... ok
test third::test::iter ... ok

test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

太好了！！！看你的吧**旁白**！我有时候是不犯错的！

> **旁白**：可整本书的意义不就在于用那些错误来教读者吗。

是啊，可有时候这一课就是我说得对，而且当我谈论不安全代码时所有人都该听我的，因为我在迭代器实现的可靠性上花的时间实在太多了？！懂吗？！懂了。

总之，这是`peek`和`peek_mut`。

```rust ,ignore
pub fn peek(&self) -> Option<&T> {
    unsafe {
        self.head.as_ref()
    }
}

pub fn peek_mut(&mut self) -> Option<&mut T> {
    unsafe {
        self.head.as_mut()
    }
}
```

我压根都不打算测它们，因为我再也不犯错了。

> **旁白**：`cargo build`

```text
error[E0308]: mismatched types
  --> src\fifth.rs:66:13
   |
25 | impl<T> List<T> {
   |      - this type parameter
...
64 |     pub fn peek(&self) -> Option<&T> {
   |                           ---------- expected `Option<&T>` 
   |                                      because of return type
65 |         unsafe {
66 |             self.head.as_ref()
   |             ^^^^^^^^^^^^^^^^^^ expected type parameter `T`, 
   |                                found struct `fifth::Node`
   |
   = note: expected enum `Option<&T>`
              found enum `Option<&fifth::Node<T>>`

```

行吧。

```rust ,ignore
pub fn peek(&self) -> Option<&T> {
    unsafe {
        self.head.as_ref().map(|node| &node.elem)
    }
}

pub fn peek_mut(&mut self) -> Option<&mut T> {
    unsafe {
        self.head.as_mut().map(|node| &mut node.elem)
    }
}
```

看来我还是会*继续*犯错，所以我们要格外小心，加一个新测试，我管它叫“miri 饲料”：一段专门到处乱搞、把我们的各种 API 混着调用的代码，好帮 miri 抓出我们的错误。

```rust ,ignore
#[test]
fn miri_food() {
    let mut list = List::new();

    list.push(1);
    list.push(2);
    list.push(3);

    assert!(list.pop() == Some(1));
    list.push(4);
    assert!(list.pop() == Some(2));
    list.push(5);

    assert!(list.peek() == Some(&3));
    list.push(6);
    list.peek_mut().map(|x| *x *= 10);
    assert!(list.peek() == Some(&30));
    assert!(list.pop() == Some(30));

    for elem in list.iter_mut() {
        *elem *= 100;
    }

    let mut iter = list.iter();
    assert_eq!(iter.next(), Some(&400));
    assert_eq!(iter.next(), Some(&500));
    assert_eq!(iter.next(), Some(&600));
    assert_eq!(iter.next(), None);
    assert_eq!(iter.next(), None);

    assert!(list.pop() == Some(400));
    list.peek_mut().map(|x| *x *= 10);
    assert!(list.peek() == Some(&5000));
    list.push(7);

    // Drop it on the ground and let the dtor exercise itself
}
```


```text
cargo test

running 16 tests
test fifth::test::basics ... ok
test fifth::test::into_iter ... ok
test fifth::test::iter ... ok
test fifth::test::iter_mut ... ok
test fifth::test::miri_food ... ok
test first::test::basics ... ok
test fourth::test::basics ... ok
test fourth::test::into_iter ... ok
test fourth::test::peek ... ok
test second::test::into_iter ... ok
test second::test::basics ... ok
test second::test::iter_mut ... ok
test second::test::peek ... ok
test third::test::iter ... ok
test second::test::iter ... ok
test third::test::basics ... ok

test result: ok. 16 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out



MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri test

running 16 tests
test fifth::test::basics ... ok
test fifth::test::into_iter ... ok
test fifth::test::iter ... ok
test fifth::test::iter_mut ... ok
test fifth::test::miri_food ... ok
test first::test::basics ... ok
test fourth::test::basics ... ok
test fourth::test::into_iter ... ok
test fourth::test::peek ... ok
test second::test::into_iter ... ok
test second::test::basics ... ok
test second::test::iter_mut ... ok
test second::test::peek ... ok
test third::test::iter ... ok
test second::test::iter ... ok
test third::test::basics ... ok

test result: ok. 16 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

完美。
