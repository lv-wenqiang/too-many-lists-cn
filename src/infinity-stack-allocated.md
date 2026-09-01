# 栈上分配的链表

这本书主要聚焦于*堆上分配*的链表，因为那是最常见也最实用的；但我们*并非*必须使用堆分配。堆分配的好处在于它让动态分配内存变得容易。栈分配在这方面就没那么友好了 &mdash; 像 C 的`alloca`这种东西被普遍认为是极其邪门而麻烦的。

那我们就用最简单的方式在栈上分配内存：调用一个函数，从而得到一个有更多空间的新栈帧！这个解法对我们的问题来说非常蠢，但同时也是真正实用而有用的。人们一直在这么干，可能压根都没把它当成链表来想！

任何时候你在递归地做某件事，都可以把指向当前这一步状态的指针传给下一步。如果那个指针本身就是状态的*一部分*，那你就造出了一个栈上分配的链表！

当然，我们现在处在本书*犯蠢*的部分，所以我们要用一种蠢办法来做这件事：让链表当主角，逼着用户的代码全都住进回调的泥潭里。人人都爱嵌套回调！

我们的 List 类型不过是一个 Node，它持有一个指向另一个 Node 的引用：

```rust
pub struct List<'a, T> {
    pub data: T,
    pub prev: Option<&'a List<'a, T>>,
}
```

而它只有一个操作，`push`，接受旧的链表、当前节点的状态，以及一个回调。新的链表将在回调中产生。我们还允许回调返回任意值，`push`会在完成时把它返回出去：

```rust ,ignore
impl<'a, T> List<'a, T> {
    pub fn push<U>(
        prev: Option<&'a List<'a, T>>, 
        data: T, 
        callback: impl FnOnce(&List<'a, T>) -> U,
    ) -> U {
        let list = List { data, prev };
        callback(&list)
    }
}
```

就这样！我们可以这样使用它：

```rust ,ignore
List::push(None, 3, |list| {
    println!("{}", list.data);
    List::push(Some(list), 5, |list| {
        println!("{}", list.data);
        List::push(Some(list), 13, |list| {
            println!("{}", list.data);
        })
    })
})
```

真美。😿

用户已经可以用 while-let 遍历`prev`值来走完这个链表了，不过纯粹为了好玩，我们还是实现一个迭代器吧，还是老一套：

```rust ,ignore
impl<'a, T> List<'a, T> {
    pub fn iter(&'a self) -> Iter<'a, T> {
        Iter { next: Some(self) }
    }
}

impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;

    fn next(&mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.prev;
            &node.data
        })
    }
}
```

我们来测试一下：

```rust ,ignore
#[cfg(test)]
mod test {
    use super::List;

    #[test]
    fn elegance() {
        List::push(None, 3, |list| {
            assert_eq!(list.iter().copied().sum::<i32>(), 3);
            List::push(Some(list), 5, |list| {
                assert_eq!(list.iter().copied().sum::<i32>(), 5 + 3);
                List::push(Some(list), 13, |list| {
                    assert_eq!(list.iter().copied().sum::<i32>(), 13 + 5 + 3);
                })
            })
        })
    }
}
```

```text
> cargo test

running 18 tests
test fifth::test::into_iter ... ok
test fifth::test::iter ... ok
test fifth::test::iter_mut ... ok
test fifth::test::basics ... ok
test fifth::test::miri_food ... ok
test first::test::basics ... ok
test second::test::into_iter ... ok
test fourth::test::peek ... ok
test fourth::test::into_iter ... ok
test second::test::iter_mut ... ok
test fourth::test::basics ... ok
test second::test::basics ... ok
test second::test::iter ... ok
test third::test::basics ... ok
test silly1::test::walk_aboot ... ok
test silly2::test::elegance ... ok
test second::test::peek ... ok
test third::test::iter ... ok

test result: ok. 18 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;
```

到这一步你可能会想“嘿，我能修改存在节点里的数据吗？”。也许可以！我们试着让链表改用可变引用而不是共享引用：


```rust
pub struct List<'a, T> {
    pub data: T,
    pub prev: Option<&'a mut List<'a, T>>,
}

pub struct Iter<'a, T> {
    next: Option<&'a List<'a, T>>,
}

impl<'a, T> List<'a, T> {
    pub fn push<U>(
        prev: Option<&'a mut List<'a, T>>, 
        data: T, 
        callback: impl FnOnce(&mut List<'a, T>) -> U,
    ) -> U {
        let mut list = List { data, prev };
        callback(&mut list)
    }

    pub fn iter(&'a self) -> Iter<'a, T> {
        Iter { next: Some(self) }
    }
}

impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;

    fn next(&mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.prev.as_ref().map(|prev| &**prev);
            &node.data
        })
    }
}

```


```text
> cargo test

error[E0521]: borrowed data escapes outside of closure
  --> src\silly2.rs:47:32
   |
46 |  List::push(Some(list), 13, |list| {
   |                              ----
   |                              |
   |              `list` declared here, outside of the closure body
   |              `list` is a reference that is only valid in the closure body
47 |      assert_eq!(list.iter().copied().sum::<i32>(), 13 + 5 + 3);
   |                 ^^^^^^^^^^^ `list` escapes the closure body here

error[E0521]: borrowed data escapes outside of closure
  --> src\silly2.rs:45:28
   |
44 |  List::push(Some(list), 5, |list| {
   |                             ----
   |                             |
   |              `list` declared here, outside of the closure body
   |              `list` is a reference that is only valid in the closure body
45 |      assert_eq!(list.iter().copied().sum::<i32>(), 5 + 3);
   |                 ^^^^^^^^^^^ `list` escapes the closure body here


<ad infinitum>
```

哎哟。看来它不喜欢我们的迭代器。也许是我们把它搞砸了？我们把测试
简化一点来查一查：


```rust ,ignore
#[test]
fn elegance() {
    List::push(None, 3, |list| {
        assert_eq!(list.data, 3);
        List::push(Some(list), 5, |list| {
            assert_eq!(list.data, 5);
            List::push(Some(list), 13, |list| {
                assert_eq!(list.data, 13);
            })
        })
    })
}
```

```text
> cargo test

error[E0521]: borrowed data escapes outside of closure
  --> src\silly2.rs:46:17
   |
44 |   List::push(Some(list), 5, |list| {
   |                              ----
   |                              |
   |              `list` declared here, outside of the closure body
   |              `list` is a reference that is only valid in the closure body
45 |       assert_eq!(list.data, 5);
46 | /     List::push(Some(list), 13, |list| {
47 | |         assert_eq!(list.data, 13);
48 | |     })
   | |______^ `list` escapes the closure body here

error[E0521]: borrowed data escapes outside of closure
  --> src\silly2.rs:44:13
   |
42 |   List::push(None, 3, |list| {
   |                        ----
   |                        |
   |              `list` declared here, outside of the closure body
   |              `list` is a reference that is only valid in the closure body
43 |       assert_eq!(list.data, 3);
44 | /     List::push(Some(list), 5, |list| {
45 | |         assert_eq!(list.data, 5);
46 | |         List::push(Some(list), 13, |list| {
47 | |             assert_eq!(list.data, 13);
48 | |         })
49 | |     })
   | |______________^ `list` escapes the closure body here
```

嗯，不对，这还是一坨热腾腾的垃圾。

问题在于，我们的链表意外地（😉）依赖了*型变*。[型变是个复杂的话题](https://doc.rust-lang.org/nomicon/subtyping.html)，不过这里我们用简化的方式来看：

每个链表都持有一个指向 List 的引用，而那个 List *和它自己的类型完全相同*。从最内层链表的视角看，这意味着所有链表用的都是和它自己相同的生命周期，可这在*客观上*是错的：链表中的每个节点都严格地比下一个活得更久，因为它们字面意义上就处在层层嵌套的作用域里！

那……为什么我们用共享引用时代码就能编译呢？因为在很多情况下，编译器知道让某个东西活得“太久”是安全的！当我们把指向某个链表的引用塞进下一个链表时，编译器悄悄地把生命周期“缩小”了，好让它们符合新链表的预期。这种生命周期的缩小就是*型变*。

这和那些带继承的语言里让你在需要 Animal（Cat 的父类型）的地方传入一个 Cat 是完全一样的把戏。直觉上我们知道，在需要 Animal 的地方传 Cat 没问题，因为 Cat 就是 Animal *再加上一些别的*。暂时忘掉“再加上一些别的”那部分是*没问题*的，对吧？

同样地，一个更大的生命周期不过就是一个更小的生命周期*再加上一些别的*。所以在这里忘掉“再加上一些别的”也没问题！

不过你现在当然会好奇：那为什么可变引用的版本就不行呢！？

嗯，型变*并不*总是安全的。如果我们那段代码*真的*编译通过了，我们就能写出这样的释放后使用：

```rust ,ignore
List::push(None, 3, |list| {
    List::push(Some(list), 5, |list| {
        List::push(Some(list), 13, |list| {
            // HAHAHA all the lifetimes are the same, so the compiler will
            // let me rewrite my parent to hold a mutable reference to myself!
            // I will create all the use-after-frees!!
            *list.prev.as_mut().unwrap().prev = Some(list);
        })
    })
})
```

忘掉细节的问题在于，*别的什么地方可能还记着那些细节，并指望它们依然成立*。
一旦你引入了*修改*，这就是个非常大的问题。如果你不小心，那些不记得我们
丢掉的“再加上一些别的”的代码，可能会觉得往那些“记着”并且*指望*
“再加上一些别的”仍然存在的地方写东西是没问题的。

用继承的说法来讲：下面这段代码必须是非法的：

```rust ,ignore
let mut my_kitty = Cat;                  // Make a Cat (long lifetime)
let animal: &mut Animal = &mut my_kitty; // Forget it's a Cat (shorten lifetime)
*animal = Dog;                           // Write a Dog (short lifetime)
my_kitty.meow();                         // Meowing Dog! (Use After Free)
```

所以，虽然你*可以*缩短一个可变引用的生命周期，但一旦你开始*嵌套*它们，
事情就变成“不变的”了，你就不再被允许缩短生命周期。

具体来说，`&mut &'big mut T`不能被转换成`&mut &'small mut T`，
其中`'big`比`'small`更大。更正式地说，`&'a mut T`对`'a`是协变的，
但对`T`是不变的。

有趣的事实：Java 其实专门*允许*你做这类事情，但它
[会做运行时检查，以防出现会喵喵叫的狗](https://docs.oracle.com/javase/7/docs/api/java/lang/ArrayStoreException.html)。

----

那我们要怎么才能修改数据呢？用内部可变性！这让我们能告诉编译器，
我们只想能够修改*数据*，而不会去动那些引用。

我们可以直接退回到之前那个用共享引用的版本，
然后在一个新测试里用上`Cell`：

```rust ,ignore
#[test]
fn cell() {
    use std::cell::Cell;

    List::push(None, Cell::new(3), |list| {
        List::push(Some(list), Cell::new(5), |list| {
            List::push(Some(list), Cell::new(13), |list| {
                // Multiply every value in the list by 10
                for val in list.iter() {
                    val.set(val.get() * 10)
                }

                let mut vals = list.iter();
                assert_eq!(vals.next().unwrap().get(), 130);
                assert_eq!(vals.next().unwrap().get(), 50);
                assert_eq!(vals.next().unwrap().get(), 30);
                assert_eq!(vals.next(), None);
                assert_eq!(vals.next(), None);
            })
        })
    })
}
```

```text
> cargo test

running 19 tests
test fifth::test::into_iter ... ok
test fifth::test::basics ... ok
test fifth::test::iter_mut ... ok
test fifth::test::iter ... ok
test fourth::test::basics ... ok
test fourth::test::into_iter ... ok
test second::test::into_iter ... ok
test first::test::basics ... ok
test fourth::test::peek ... ok
test second::test::basics ... ok
test fifth::test::miri_food ... ok
test silly2::test::cell ... ok
test third::test::iter ... ok
test second::test::iter_mut ... ok
test second::test::peek ... ok
test silly1::test::walk_aboot ... ok
test silly2::test::elegance ... ok
test third::test::basics ... ok
test second::test::iter ... ok

test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;
```

简单得像递归派一样！✨
